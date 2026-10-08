"""Local, read-only simulation dashboard. No network integrations or order entry."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st

from lab.reports import SnapshotError, build_daily_report, empty_snapshot, parse_snapshot


def _number(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or (amount != 0 and not -18 <= amount.adjusted() <= 18):
            return None
        return amount
    except (InvalidOperation, ValueError):
        return None


def _clp(value):
    amount = _number(value)
    return "Sin datos" if amount is None else f"${amount:,.0f} CLP".replace(",", ".")


def _percent(value):
    amount = _number(value)
    return "Sin datos" if amount is None else f"{amount * 100:.2f}%".replace(".", ",")


st.set_page_config(page_title="Atalaya — AI Trading Lab", page_icon="🔭", layout="wide")
st.title("Atalaya · AI Trading Lab")
st.caption("SIMULACIÓN · Investigación y disciplina del capital · Sin ejecución de órdenes")
st.info("Panel local: carga un JSON para inspeccionarlo en memoria. No se conecta a mercados, cuentas ni servicios externos.")

if "snapshot" not in st.session_state:
    st.session_state.snapshot = empty_snapshot()
if "upload_generation" not in st.session_state:
    st.session_state.upload_generation = 0

with st.sidebar:
    st.subheader("Datos de la sesión")
    st.caption("Solo JSON en modo paper, máximo 1 MiB. Sin credenciales. No se guardan archivos cargados.")
    uploaded = st.file_uploader("Cargar instantánea JSON", type=["json"],
                                key=f"upload_{st.session_state.upload_generation}")
    if uploaded is not None:
        try:
            st.session_state.snapshot = parse_snapshot(uploaded.getvalue())
            st.success("Instantánea cargada en memoria.")
        except SnapshotError as exc:
            st.session_state.snapshot = empty_snapshot()
            st.error(str(exc))
    if st.button("Ver ejemplo sintético", use_container_width=True):
        try:
            # This fixed, project-owned file is the only disk read performed by the app.
            raw = (Path(__file__).parent / "data" / "demo.json").read_bytes()
            demo = parse_snapshot(raw)
            if not demo["synthetic"]:
                raise SnapshotError("El ejemplo debe identificarse como sintético.")
            st.session_state.snapshot = demo
            st.session_state.upload_generation += 1
            st.rerun()
        except (OSError, SnapshotError):
            st.error("El ejemplo sintético no está disponible o no tiene un formato válido.")
    if st.button("Vaciar sesión", use_container_width=True):
        st.session_state.snapshot = empty_snapshot()
        st.session_state.upload_generation += 1
        st.rerun()
    st.caption("Las aprobaciones declaradas en archivos no autentican votos. Emite y revisa votos mediante el expediente humano en GitHub.")

snapshot = st.session_state.snapshot
try:
    report = build_daily_report(snapshot, datetime.now(timezone.utc))
except (ValueError, TypeError, KeyError, ArithmeticError):
    st.error("No se pudo evaluar la instantánea. Revisa el formato y los datos de la configuración.")
    st.stop()

if report["synthetic"]:
    st.warning("EJEMPLO SINTÉTICO: sus activos, precios y resultados son ficticios; no indican una oportunidad real.")
else:
    st.caption("Instantánea declarada por el usuario; fuentes, aprobaciones y vigencia no se verifican externamente.")

summary_tab, market_tab, trades_tab, team_tab = st.tabs(["Resumen", "Mercado", "Operaciones", "Equipo"])

with summary_tab:
    if report["status"] == "NO_OPERAR":
        st.error("NO OPERAR")
    else:
        st.warning("Propuestas para simulación sujetas a revisión humana.")
    for reason in report["reasons"]:
        st.text(reason)
    st.subheader("Resultados netos de ejecución antes de impuestos")
    st.caption("Métricas calculadas sobre operaciones simuladas cerradas. No prometen rentabilidad futura.")
    metrics = report["summary"]
    columns = st.columns(4)
    columns[0].metric("Patrimonio simulado", _clp(metrics.get("equity_clp")))
    columns[1].metric("Resultado neto", _clp(metrics.get("net_pnl_clp")))
    columns[2].metric("Operaciones ganadoras", _percent(metrics.get("win_rate")))
    columns[3].metric("Caída máxima observada", _percent(metrics.get("max_drawdown_fraction")))
    secondary = st.columns(3)
    secondary[0].metric("Rentabilidad de ejecución", _percent(metrics.get("return_fraction")))
    secondary[1].metric("Costes de ejecución", _clp(metrics.get("costs_clp")))
    secondary[2].metric("Operaciones cerradas", str(metrics.get("closed_trades", 0)))
    st.caption("La caída y el patrimonio requieren una curva que incluya posiciones abiertas para reflejar la sesión completa.")
    with st.expander("Detalle de los cálculos"):
        st.json(metrics)
    st.subheader("Informe diario")
    st.download_button("Descargar informe de simulación", data=report["markdown"],
                       file_name="atalaya-informe-simulacion.md", mime="text/markdown")
    with st.expander("Vista del informe como texto"):
        st.text(report["markdown"])

with market_tab:
    st.subheader("Situación declarada del mercado")
    st.text(snapshot["market_context"])
    if snapshot["sources"]:
        st.subheader("Fuentes declaradas")
        st.json(snapshot["sources"])
    st.subheader("Lista de observación")
    if snapshot["watchlist"]:
        st.json(snapshot["watchlist"])
    else:
        st.caption("Sin activos configurados.")
    st.subheader("Oportunidades · hasta tres")
    if not report["opportunities"]:
        st.info("NO OPERAR: no existe una oportunidad confiable evaluable.")
    for index, item in enumerate(report["opportunities"], 1):
        with st.expander(f"Propuesta {index}", expanded=True):
            # st.json renders supplied text inertly and never interprets HTML or instructions.
            st.json(item["opportunity"])
            st.text(f"Gestor de riesgos: {item['risk'].get('status', 'NO_OPERAR')}")
            for reason in item["risk"].get("reasons", []):
                st.text(reason)
            st.json(item["risk"].get("metrics", {}))

with trades_tab:
    st.subheader("Historial de operaciones simuladas")
    st.caption("El MVP acepta exclusivamente modo paper. Registra costes y monedas; conserva los registros reales en otro expediente.")
    if snapshot["trades"]:
        st.json(snapshot["trades"])
    else:
        st.info("Todavía no hay operaciones simuladas registradas.")
    st.subheader("Comparación con referencias")
    st.caption("Pendiente: selecciona una referencia, mismo período y moneda antes del experimento. No se calcula una comparación sin esos datos.")

with team_tab:
    st.subheader("Votaciones · inspección del expediente")
    st.caption("Esta vista no vota, ratifica ni autentica integrantes. Dos aprobaciones con silencio requieren verificación y ratificación separadas.")
    st.text(f"Estado de inspección: {report['ballot'].get('status', 'DRAFT')}")
    for reason in report["ballot"].get("reasons", []):
        st.text(reason)
    st.caption("Autorización de operación real: NO. Aprobación de estrategia y autorización de orden son expedientes distintos.")
    if snapshot["governance"].get("votes"):
        st.json(snapshot["governance"]["votes"])
    st.subheader("Registro declarado de los agentes")
    if snapshot["agent_decisions"]:
        st.json(snapshot["agent_decisions"])
    else:
        st.info("Sin conclusiones registradas. Los agentes se invocan por tarea; no son servicios activos continuamente.")
