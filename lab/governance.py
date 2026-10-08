"""Local, fail-closed evaluation of authenticated weekly ballot evidence.

This module does not authenticate GitHub accounts, fetch comments, write decisions,
ratify silence, or authorize orders. A future trusted collector must independently
establish provenance, access and complete evidence before invoking it. Flags in an
uploaded JSON file are not authentication and must not be trusted by a frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

EVALUATOR_VERSION = "0.1.0"
SEALED_FIELDS = (
    "id", "revision", "content", "member_ids", "opened_at", "deadline",
    "valid_from", "valid_until", "governance_version", "policy_sha256", "commit_sha",
)


def proposal_digest(payload: dict[str, Any]) -> str:
    """SHA-256 of strict canonical JSON, without executing any supplied content."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sealed_payload(proposal: dict[str, Any]) -> dict[str, Any]:
    """All material fields covered by ``sealed_digest``; no mutable evidence."""
    return {field: proposal.get(field) for field in SEALED_FIELDS}


def _time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("missing timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _numeric_id(value: Any) -> bool:
    return type(value) is int and value > 0


def evaluate_ballot(
    proposal: dict[str, Any], votes: list[dict[str, Any]], now: datetime,
) -> dict[str, Any]:
    """Evaluate a sealed strategy ballot; never grants real-order authority.

    Three verified human approvals can produce APPROVED_UNANIMOUS. Two and true
    silence after the deadline only produce WAITING_RATIFICATION. Ratification
    requires a separate future implementation with independent safety controls.
    """
    result: dict[str, Any] = {
        "status": "DRAFT", "reasons": [], "approvals": [],
        "scope": "strategy", "real_order_authorized": False,
        "evaluator_version": EVALUATOR_VERSION,
        "proposal_id": proposal.get("id") if isinstance(proposal, dict) else None,
        "sealed_digest": proposal.get("sealed_digest") if isinstance(proposal, dict) else None,
        "evaluated_at": None, "ignored_events": [],
    }

    def finish(status: str, *reasons: str) -> dict[str, Any]:
        result["status"] = status
        result["reasons"].extend(reasons)
        return result

    try:
        current = _time(now)
        result["evaluated_at"] = current.isoformat()
    except (ValueError, TypeError, OverflowError):
        return finish("HUMAN_REVIEW", "Evaluation time must be timezone-aware.")
    if not isinstance(proposal, dict) or not isinstance(votes, list):
        return finish("DRAFT", "Proposal and votes must use the supported schema.")

    members = proposal.get("member_ids")
    if (
        not isinstance(members, list) or len(members) != 3
        or not all(_numeric_id(member) for member in members)
        or len(set(members)) != 3
    ):
        return finish("DRAFT", "Exactly three distinct numeric human member IDs are required.")
    if (
        not isinstance(proposal.get("id"), str) or not proposal["id"].strip()
        or type(proposal.get("revision")) is not int or proposal["revision"] < 1
        or not isinstance(proposal.get("content"), dict) or not proposal["content"]
        or not isinstance(proposal.get("governance_version"), str)
        or not proposal["governance_version"].strip()
        or not _hash(proposal.get("policy_sha256"))
        or not isinstance(proposal.get("commit_sha"), str)
        or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", proposal["commit_sha"]) is None
        or not _hash(proposal.get("sealed_digest"))
    ):
        return finish("DRAFT", "Proposal ID, revision, content, versions and hashes must be complete.")
    try:
        actual_digest = proposal_digest(sealed_payload(proposal))
    except (ValueError, TypeError, OverflowError):
        return finish("HUMAN_REVIEW", "Proposal cannot be represented by strict canonical JSON.")
    if actual_digest != proposal["sealed_digest"]:
        return finish("HUMAN_REVIEW", "Sealed proposal changed; a new revision and new votes are required.")
    try:
        opened = _time(proposal.get("opened_at"))
        deadline = _time(proposal.get("deadline"))
        valid_from = _time(proposal.get("valid_from"))
        valid_until = _time(proposal.get("valid_until"))
    except (ValueError, TypeError, OverflowError):
        return finish("DRAFT", "Opening, deadline and validity require timezone-aware timestamps.")
    if not opened < deadline <= valid_from < valid_until:
        return finish("DRAFT", "Ballot and strategy validity intervals are inconsistent.")
    if proposal.get("superseded") is True:
        return finish("SUPERSEDED", "A newer proposal revision supersedes this ballot.")
    if current >= valid_until:
        return finish("EXPIRED", "Strategy validity ended; weekly confirmation is required.")
    if current < opened:
        return finish("DRAFT", "Voting has not opened.")

    required_evidence = (
        "trusted_collector", "evidence_complete", "integrity_verified", "repository_private",
    )
    failures = [name for name in required_evidence if proposal.get(name) is not True]
    if failures:
        return finish("HUMAN_REVIEW", "Missing independent evidence controls: " + ", ".join(failures) + ".")
    invitations = proposal.get("invitation_evidence")
    if not isinstance(invitations, list) or len(invitations) != 3:
        return finish("HUMAN_REVIEW", "Invitation and access evidence is required for all three humans.")
    invitation_ids: set[int] = set()
    for invitation in invitations:
        if not isinstance(invitation, dict):
            return finish("HUMAN_REVIEW", "Malformed invitation evidence.")
        member = invitation.get("member_id")
        if not _numeric_id(member) or member not in members or member in invitation_ids:
            return finish("HUMAN_REVIEW", "Invitation identity is missing, repeated or outside the team.")
        invitation_ids.add(member)
        try:
            sent = _time(invitation.get("sent_at"))
        except (ValueError, TypeError, OverflowError):
            return finish("HUMAN_REVIEW", "Invitation time must be verified.")
        if (
            not opened <= sent < deadline or sent > current
            or invitation.get("delivery_verified") is not True
            or invitation.get("access_verified") is not True
            or not isinstance(invitation.get("evidence_url"), str)
            or not invitation["evidence_url"].strip()
        ):
            return finish("HUMAN_REVIEW", "A human did not receive a verified opportunity to vote.")

    approvals: set[int] = set()
    responded: set[int] = set()
    events: dict[str, str] = {}
    sticky_issues: list[str] = []
    for vote in votes:
        if not isinstance(vote, dict):
            sticky_issues.append("Malformed vote evidence.")
            continue
        member = vote.get("member_id")
        if not _numeric_id(member) or member not in members:
            result["ignored_events"].append(vote.get("event_id"))
            continue
        if vote.get("actor_verified") is not True or vote.get("is_human") is not True:
            sticky_issues.append("A team identity or human voter could not be authenticated.")
            continue
        event = vote.get("event_id")
        if not isinstance(event, str) or not event.strip():
            sticky_issues.append("A vote lacks a stable evidence event ID.")
            continue
        try:
            evidence_digest = proposal_digest(vote)
        except (ValueError, TypeError, OverflowError):
            sticky_issues.append("Vote evidence cannot be represented by strict canonical JSON.")
            continue
        if event in events:
            if events[event] != evidence_digest:
                sticky_issues.append("The same evidence event has conflicting content.")
            continue
        events[event] = evidence_digest
        if vote.get("edited") is True or vote.get("deleted") is True:
            sticky_issues.append("Edited or deleted vote requires human review.")
        if not isinstance(vote.get("evidence_url"), str) or not vote["evidence_url"].strip():
            sticky_issues.append("Vote source evidence is missing.")
        try:
            created = _time(vote.get("created_at"))
            received = _time(vote.get("received_at"))
        except (ValueError, TypeError, OverflowError):
            sticky_issues.append("Vote timestamps must be authenticated and timezone-aware.")
            continue
        if created > current or received > current or received < created:
            sticky_issues.append("Vote evidence has future or inconsistent timestamps.")
            continue
        if (
            vote.get("proposal_id") != proposal["id"]
            or vote.get("revision") != proposal["revision"]
            or vote.get("sealed_digest") != proposal["sealed_digest"]
        ):
            sticky_issues.append("A human responded to another revision or sealed digest.")
            continue
        decision = vote.get("decision")
        if decision != "APPROVE":
            # Opposition, withdrawal, abstention and ambiguity are sticky, even
            # after the deadline. A subsequent approval cannot erase them.
            sticky_issues.append("Opposition, withdrawal, abstention or ambiguous response requires human review.")
        if created < opened:
            sticky_issues.append("Vote was created before the ballot opened.")
            continue
        responded.add(member)
        if created >= deadline:
            if decision == "APPROVE":
                sticky_issues.append("A late response cannot count as approval or as silence.")
            continue
        if decision == "APPROVE":
            approvals.add(member)

    result["approvals"] = sorted(approvals)
    if sticky_issues:
        return finish("HUMAN_REVIEW", *dict.fromkeys(sticky_issues))
    if len(approvals) == 3:
        return finish("APPROVED_UNANIMOUS", "Three authenticated humans approved the same sealed revision.")
    if current < deadline:
        return finish("OPEN", "Voting remains open; insufficient approvals do not close it early.")
    if len(approvals) == 2 and len(responded) == 2:
        return finish("WAITING_RATIFICATION", "Deadline passed with two approvals and verified silence; separate AI ratification is required.")
    return finish("HUMAN_REVIEW", "Deadline passed without the required approvals and verified silence.")
