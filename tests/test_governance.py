"""Synthetic ballot evidence only; these IDs identify no project members."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from lab.governance import evaluate_ballot, proposal_digest, sealed_payload


OPENED = datetime(2030, 1, 4, 18, tzinfo=timezone.utc)
DEADLINE = OPENED + timedelta(days=2)


def proposal_fixture():
    proposal = {
        "id": "synthetic-week-01", "revision": 1,
        "content": {"mode": "paper", "strategy": "synthetic test only"},
        "member_ids": [101, 102, 103], "opened_at": OPENED.isoformat(),
        "deadline": DEADLINE.isoformat(), "valid_from": DEADLINE.isoformat(),
        "valid_until": (DEADLINE + timedelta(days=7)).isoformat(),
        "governance_version": "0.1", "policy_sha256": "a" * 64,
        "commit_sha": "b" * 40, "trusted_collector": True,
        "evidence_complete": True, "integrity_verified": True,
        "repository_private": True,
        "invitation_evidence": [
            {"member_id": member, "sent_at": OPENED.isoformat(),
             "access_verified": True, "delivery_verified": True,
             "evidence_url": "https://example.invalid/invitation/" + str(member)}
            for member in [101, 102, 103]
        ],
    }
    proposal["sealed_digest"] = proposal_digest(sealed_payload(proposal))
    return proposal


def vote_fixture(proposal, member, decision="APPROVE", created=None):
    created = created or OPENED + timedelta(hours=1)
    return {
        "event_id": "synthetic-" + str(member) + "-" + decision,
        "member_id": member, "is_human": True, "actor_verified": True,
        "proposal_id": proposal["id"], "revision": proposal["revision"],
        "sealed_digest": proposal["sealed_digest"], "decision": decision,
        "created_at": created.isoformat(), "received_at": created.isoformat(),
        "evidence_url": "https://example.invalid/vote/" + str(member),
    }


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.proposal = proposal_fixture()
        self.votes = [vote_fixture(self.proposal, member) for member in [101, 102, 103]]

    def evaluate(self, votes=None, now=None, proposal=None):
        result = evaluate_ballot(
            self.proposal if proposal is None else proposal,
            self.votes if votes is None else votes,
            now or DEADLINE + timedelta(seconds=1),
        )
        self.assertFalse(result["real_order_authorized"])
        self.assertEqual(result["scope"], "strategy")
        return result

    def test_unanimous_and_repeat_approval(self):
        self.assertEqual(self.evaluate()["status"], "APPROVED_UNANIMOUS")
        votes = self.votes + [deepcopy(self.votes[0])]
        repeat = vote_fixture(self.proposal, 101, created=OPENED + timedelta(hours=2))
        repeat["event_id"] = "synthetic-repeat"
        votes.append(repeat)
        result = self.evaluate(votes)
        self.assertEqual(result["status"], "APPROVED_UNANIMOUS")
        self.assertEqual(result["approvals"], [101, 102, 103])

    def test_two_approvals_before_and_after_deadline(self):
        self.assertEqual(self.evaluate(self.votes[:2], DEADLINE - timedelta(seconds=1))["status"], "OPEN")
        self.assertEqual(self.evaluate(self.votes[:2], DEADLINE)["status"], "WAITING_RATIFICATION")
        self.assertEqual(self.evaluate(self.votes[:1])["status"], "HUMAN_REVIEW")

    def test_opposition_withdrawal_abstention_and_ambiguity_are_sticky(self):
        for decision in ["OPPOSE", "WITHDRAW", "ABSTAIN", "no, I disagree", None]:
            with self.subTest(decision=decision):
                vote = vote_fixture(self.proposal, 103)
                vote["decision"] = decision
                vote["event_id"] = "synthetic-response"
                self.assertEqual(self.evaluate(self.votes + [vote])["status"], "HUMAN_REVIEW")

    def test_bot_and_unverified_team_identity_do_not_count(self):
        for flag in ["is_human", "actor_verified"]:
            with self.subTest(flag=flag):
                votes = deepcopy(self.votes)
                votes[2][flag] = False
                result = self.evaluate(votes)
                self.assertEqual(result["status"], "HUMAN_REVIEW")
                self.assertNotIn(103, result["approvals"])
        outsider = vote_fixture(self.proposal, 999)
        outsider["is_human"] = False
        self.assertEqual(self.evaluate(self.votes[:2] + [outsider])["status"], "WAITING_RATIFICATION")

    def test_old_hash_and_mutated_sealed_fields_are_blocked(self):
        votes = deepcopy(self.votes)
        votes[2]["sealed_digest"] = "c" * 64
        self.assertEqual(self.evaluate(votes)["status"], "HUMAN_REVIEW")
        changes = {
            "id": "changed", "revision": 2, "member_ids": [201, 202, 203],
            "deadline": (DEADLINE + timedelta(hours=1)).isoformat(),
            "policy_sha256": "c" * 64, "commit_sha": "c" * 40,
            "governance_version": "different", "content": {"mode": "real"},
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                proposal = deepcopy(self.proposal)
                proposal[field] = value
                self.assertEqual(self.evaluate(proposal=proposal)["status"], "HUMAN_REVIEW")

    def test_edited_deleted_and_conflicting_event_require_review(self):
        for field in ["edited", "deleted"]:
            with self.subTest(field=field):
                votes = deepcopy(self.votes)
                votes[2][field] = True
                self.assertEqual(self.evaluate(votes)["status"], "HUMAN_REVIEW")
        changed = deepcopy(self.votes[0])
        changed["decision"] = "OPPOSE"
        self.assertEqual(self.evaluate(self.votes + [changed])["status"], "HUMAN_REVIEW")

    def test_vote_exactly_at_deadline_is_late(self):
        votes = self.votes[:2] + [vote_fixture(self.proposal, 103, created=DEADLINE)]
        result = self.evaluate(votes)
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertEqual(result["approvals"], [101, 102])

    def test_received_late_counts_when_created_before_deadline(self):
        votes = deepcopy(self.votes)
        votes[2]["received_at"] = (DEADLINE + timedelta(seconds=1)).isoformat()
        self.assertEqual(self.evaluate(votes)["status"], "APPROVED_UNANIMOUS")

    def test_late_opposition_suspends_unanimous_approval(self):
        vote = vote_fixture(self.proposal, 103, "OPPOSE", DEADLINE + timedelta(seconds=1))
        self.assertEqual(self.evaluate(self.votes + [vote])["status"], "HUMAN_REVIEW")

    def test_incomplete_evidence_and_public_repository_never_approve(self):
        for flag in ["trusted_collector", "evidence_complete", "integrity_verified", "repository_private"]:
            with self.subTest(flag=flag):
                proposal = deepcopy(self.proposal)
                proposal[flag] = False
                self.assertEqual(self.evaluate(proposal=proposal)["status"], "HUMAN_REVIEW")
        for field in ["delivery_verified", "access_verified"]:
            with self.subTest(field=field):
                proposal = deepcopy(self.proposal)
                proposal["invitation_evidence"][2][field] = False
                self.assertEqual(self.evaluate(proposal=proposal)["status"], "HUMAN_REVIEW")

    def test_invalid_invitation_times_and_missing_members(self):
        proposal = deepcopy(self.proposal)
        proposal["invitation_evidence"][2]["sent_at"] = DEADLINE.isoformat()
        self.assertEqual(self.evaluate(proposal=proposal)["status"], "HUMAN_REVIEW")
        proposal = deepcopy(self.proposal)
        proposal["invitation_evidence"].pop()
        self.assertEqual(self.evaluate(proposal=proposal)["status"], "HUMAN_REVIEW")

    def test_future_naive_and_inconsistent_vote_times(self):
        for field, value in [
            ("created_at", (DEADLINE + timedelta(days=1)).isoformat()),
            ("received_at", (DEADLINE + timedelta(days=1)).isoformat()),
            ("received_at", OPENED.isoformat()),
            ("created_at", "2030-01-04T19:00:00"),
        ]:
            with self.subTest(field=field, value=value):
                votes = deepcopy(self.votes)
                votes[2][field] = value
                self.assertEqual(self.evaluate(votes)["status"], "HUMAN_REVIEW")
        self.assertEqual(self.evaluate(now=datetime(2030, 1, 6, 18))["status"], "HUMAN_REVIEW")

    def test_invalid_schema_draft_expired_and_superseded(self):
        for members in [[], [101, 102, 102], [101, 102, True], ["101", 102, 103]]:
            with self.subTest(members=members):
                proposal = deepcopy(self.proposal)
                proposal["member_ids"] = members
                self.assertEqual(self.evaluate(proposal=proposal)["status"], "DRAFT")
        self.assertEqual(self.evaluate(now=OPENED - timedelta(seconds=1))["status"], "DRAFT")
        self.assertEqual(self.evaluate(now=DEADLINE + timedelta(days=7))["status"], "EXPIRED")
        proposal = deepcopy(self.proposal)
        proposal["superseded"] = True
        self.assertEqual(self.evaluate(proposal=proposal)["status"], "SUPERSEDED")
        self.assertEqual(self.evaluate(proposal={})["status"], "DRAFT")

    def test_deterministic_evaluation_has_no_side_effects(self):
        proposal_copy, votes_copy = deepcopy(self.proposal), deepcopy(self.votes)
        one = self.evaluate()
        two = self.evaluate()
        self.assertEqual(one, two)
        self.assertEqual(self.proposal, proposal_copy)
        self.assertEqual(self.votes, votes_copy)

    def test_hash_uses_strict_canonical_json(self):
        self.assertEqual(proposal_digest({"a": 1, "b": 2}), proposal_digest({"b": 2, "a": 1}))
        with self.assertRaises(ValueError):
            proposal_digest({"unsupported": float("nan")})


if __name__ == "__main__":
    unittest.main()
