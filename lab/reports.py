"""Pure report assembly and bounded, inert JSON snapshot parsing.

Snapshots are user supplied claims, never evidence of authenticated votes or live
prices. No files, URLs, account connections or commands are accessed here.
"""

from __future__ import annotations

import copy
import html
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

MAX_UPLOAD_BYTES = 1024 * 1024
MAX_DEPTH = 12
MAX_NODES = 10000
MAX_RECORDS = 1000
MAX_TEXT_LENGTH = 4000
COLLECTIONS = ("opportunities", "trades", "watchlist", "sources", "agent_decisions", "equity_curve")
SECRET_FIELDS = {
    "api_key", "apikey", "api_secret", "secret", "password", "credentials",
    "private_key", "access_token", "refresh_token", "token", "authorization",
}


class SnapshotError(ValueError):
    """A bounded, public-safe validation error without private input excerpts."""


def empty_snapshot() -> dict[str, Any]:
    return {
        "schema_version": 1, "mode": "paper", "synthetic": False,
        "policy": {}, "account": {}, "opportunities": [], "trades": [],
        "watchlist": [], "sources": [], "agent_decisions": [],
        "equity_curve": [], "governance": {"proposal": {}, "votes": []},
        "market_context": "Sin datos de mercado verificados.",
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("El JSON contiene claves duplicadas.")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise SnapshotError("El JSON contiene un número no finito.")


def parse_snapshot(raw: bytes | str) -> dict[str, Any]:
    """Decode at most 1 MiB of UTF-8 JSON, rejecting ambiguous numeric data."""
    if not isinstance(raw, (bytes, str)):
        raise SnapshotError("Se requiere un archivo JSON.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise SnapshotError("El archivo supera el límite de 1 MiB.")
    try:
        encoded = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        if len(encoded) > MAX_UPLOAD_BYTES:
            raise SnapshotError("El archivo supera el límite de 1 MiB.")
        value = json.loads(encoded.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except SnapshotError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise SnapshotError("El archivo no es un JSON UTF-8 válido.") from None
    return normalize_snapshot(value)


def _inspect(value: Any, depth: int, budget: list[int]) -> None:
    budget[0] += 1
    if depth > MAX_DEPTH or budget[0] > MAX_NODES:
        raise SnapshotError("El JSON supera los límites de estructura.")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 100:
                raise SnapshotError("El JSON contiene una clave inválida.")
            if key.lower() in SECRET_FIELDS:
                raise SnapshotError("El archivo contiene campos de credenciales; retíralos antes de cargarlo.")
            if key.lower() == "mode" and item != "paper":
                raise SnapshotError("Solo se aceptan registros con modo paper (simulación).")
            _inspect(item, depth + 1, budget)
    elif isinstance(value, list):
        if len(value) > MAX_RECORDS:
            raise SnapshotError("Una colección supera el límite de 1000 registros.")
        for item in value:
            _inspect(item, depth + 1, budget)
    elif isinstance(value, str):
        if len(value) > MAX_TEXT_LENGTH or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise SnapshotError("El JSON contiene texto demasiado largo o caracteres de control.")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise SnapshotError("El JSON contiene un número no finito.")
    elif value is not None and not isinstance(value, (bool, int)):
        raise SnapshotError("El JSON contiene un tipo de dato no compatible.")


def normalize_snapshot(value: Any) -> dict[str, Any]:
    """Validate and copy; do not mutate the caller's data or silently use real mode."""
    if not isinstance(value, dict):
        raise SnapshotError("El documento debe ser un objeto JSON.")
    _inspect(value, 0, [0])
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise SnapshotError("Se requiere schema_version: 1.")
    if value.get("mode") != "paper":
        raise SnapshotError("Solo se acepta mode: paper (simulación).")
    if "synthetic" in value and not isinstance(value["synthetic"], bool):
        raise SnapshotError("synthetic debe ser verdadero o falso.")
    snapshot = empty_snapshot()
    snapshot.update(copy.deepcopy(value))
    for name in COLLECTIONS:
        if not isinstance(snapshot[name], list) or any(not isinstance(row, dict) for row in snapshot[name]):
            raise SnapshotError("Las colecciones deben contener objetos JSON.")
    for name in ("policy", "account", "governance"):
        if not isinstance(snapshot[name], dict):
            raise SnapshotError("La configuración y gobernanza deben ser objetos JSON.")
    governance = snapshot["governance"]
    if not isinstance(governance.get("proposal", {}), dict):
        raise SnapshotError("La propuesta debe ser un objeto JSON.")
    if not isinstance(governance.get("votes", []), list) or any(
        not isinstance(vote, dict) for vote in governance.get("votes", [])
    ):
        raise SnapshotError("Los votos deben ser una lista de objetos JSON.")
    if not isinstance(snapshot["market_context"], str):
        raise SnapshotError("El contexto de mercado debe ser texto.")
    return snapshot


def safe_text(value: Any) -> str:
    """Make untrusted content inert when a downloaded report is read as Markdown."""
    if value is None:
        return "No disponible"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    value = html.escape(str(value), quote=True)
    value = re.sub(r"([\\`*{}\[\]()#+.!|_>~-])", r"\\\1", value)
    return value.replace("\r", " ").replace("\n", " / ")


def _aware_now(now: datetime | None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise SnapshotError("La hora de evaluación debe incluir zona horaria.")
    return now.astimezone(timezone.utc)


def build_daily_report(value: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Build a simulation-only report; imported snapshot trust flags are revoked."""
    from lab.governance import evaluate_ballot
    from lab.ledger import summarize_ledger
    from lab.risk import evaluate_risk

    snapshot = normalize_snapshot(value)
    now = _aware_now(now)
    account_for_risk = copy.deepcopy(snapshot["account"])
    # Approval claims in uploaded files do not establish human authorization.
    account_for_risk["strategy_approved"] = False
    opportunities = []
    for opportunity in snapshot["opportunities"][:3]:
        result = evaluate_risk(snapshot["policy"], account_for_risk, opportunity, now)
        opportunities.append({"opportunity": opportunity, "risk": result})
    summary = summarize_ledger(snapshot["trades"], snapshot["account"].get("capital_initial_clp"),
                               equity_curve=snapshot["equity_curve"] or None)
    governance = snapshot["governance"]
    proposal = copy.deepcopy(governance.get("proposal", {}))
    # Files cannot authenticate collection, access, membership or votes.
    for flag in ("trusted_collector", "evidence_complete", "integrity_verified",
                 "invitations_verified", "access_verified"):
        proposal[flag] = False
    ballot = evaluate_ballot(proposal, governance.get("votes", []), now)
    status = "NO_OPERAR"
    if opportunities and any(item["risk"].get("status") == "APTO_PARA_SIMULAR" for item in opportunities):
        status = "PROPUESTAS_PARA_SIMULACION"
    if not opportunities:
        overall_reasons = ["No hay oportunidades con datos suficientes; no existe una oportunidad confiable evaluable."]
    else:
        overall_reasons = ["El archivo es una instantánea suministrada; no verifica cotizaciones ni aprobaciones externas.",
                           "Las aprobaciones declaradas no autorizan entradas: requieren un expediente humano verificado."]
    if len(snapshot["opportunities"]) > 3:
        overall_reasons.append("El informe limita la evaluación a las primeras tres oportunidades.")
    report = {
        "status": status, "mode": "paper", "synthetic": snapshot["synthetic"],
        "generated_at": now.isoformat(), "opportunities": opportunities,
        "summary": summary, "ballot": ballot, "reasons": overall_reasons,
        "snapshot": snapshot,
    }
    report["markdown"] = _render_report(report)
    return report


def _render_report(report: dict[str, Any]) -> str:
    snapshot = report["snapshot"]
    lines = [
        "# ATALAYA — Informe diario", "", "**Modo: SIMULACIÓN. Sin autorización de órdenes reales.**",
        "", "**Datos sintéticos de demostración; no son cotizaciones ni resultados reales.**" if report["synthetic"]
        else "Instantánea aportada por el usuario; no representa datos verificados en vivo.",
        "", f"Fecha de elaboración UTC: {safe_text(report['generated_at'])}",
        f"Estado: {safe_text(report['status'])}", "",
        "## Situación del mercado", "", safe_text(snapshot["market_context"]), "",
        "Fuentes declaradas (sin verificación automática):",
    ]
    for source in snapshot["sources"]:
        lines.append(f"- {safe_text(source)}")
    if not snapshot["sources"]:
        lines.append("- Sin fuentes de mercado configuradas.")
    lines += ["", "## Oportunidades — máximo tres", ""]
    if not report["opportunities"]:
        lines.append("**NO OPERAR. No existe una oportunidad confiable evaluable.**")
    fields = (
        ("Activo", "symbol"), ("Mercado", "market"), ("Moneda", "currency"),
        ("Bid", "bid"), ("Ask / entrada", "ask"), ("Hora del dato", "market_timestamp"),
        ("Hora de recepción", "received_timestamp"), ("Fuente", "source"),
        ("Justificación", "rationale"), ("Objetivo", "target"), ("Stop", "stop"),
        ("Invalidación", "invalidation"), ("Vigencia", "expires_at"),
        ("Confianza y fundamento", "confidence"), ("Incertidumbres", "uncertainties"),
    )
    for index, item in enumerate(report["opportunities"], 1):
        lines += ["", f"### Propuesta {index}", ""]
        opportunity, risk = item["opportunity"], item["risk"]
        for label, key in fields:
            lines.append(f"- {label}: {safe_text(opportunity.get(key))}")
        lines += [f"- Gestor de riesgos: {safe_text(risk.get('status'))}",
                  f"- Cálculos netos y costes: {safe_text(risk.get('metrics', {}))}"]
        lines.extend(f"- Motivo: {safe_text(reason)}" for reason in risk.get("reasons", []))
    lines += ["", "## Decisión consolidada", ""]
    lines.extend(f"- {safe_text(reason)}" for reason in report["reasons"])
    lines += ["", "## Seguimiento de simulaciones", "",
              "Resultados netos de ejecución antes de impuestos; sin inferencia de rentabilidad futura.", ""]
    for key, value in report["summary"].items():
        lines.append(f"- {safe_text(key)}: {safe_text(value)}")
    lines += ["", "## Gobernanza — inspección del archivo", "",
              f"- Estado: {safe_text(report['ballot'].get('status'))}",
              "- Los votos y banderas de confianza cargados no se consideran autenticados.",
              "- Aprobar una estrategia no autoriza una operación real.", "",
              "## Conclusiones declaradas de agentes", ""]
    for decision in snapshot["agent_decisions"]:
        lines.append(f"- {safe_text(decision)}")
    if not snapshot["agent_decisions"]:
        lines.append("- Sin conclusiones registradas. Los agentes no están ejecutándose continuamente.")
    return "\n".join(lines) + "\n"


def render_daily_report(value: dict[str, Any], now: datetime | None = None) -> str:
    return build_daily_report(value, now)["markdown"]
