import os
import sys

_path = os.path.join(os.path.dirname(__file__), "..", "api")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _path)

from query_understanding import detect_topic


class TestIntentExtraction:
    def test_intent_permission(self):
        q = detect_topic("Can society appoint expert director?")
        assert q.intent == "authority", f"Expected authority, got {q.intent}"

    def test_intent_eligibility(self):
        q = detect_topic("Can member become committee member?")
        assert q.intent == "eligibility", f"Expected eligibility, got {q.intent}"

    def test_intent_prohibition(self):
        q = detect_topic("Can committee remove secretary without notice?")
        assert q.intent == "authority", f"Expected authority, got {q.intent}"

    def test_intent_procedure(self):
        q = detect_topic("How to transfer share certificate?")
        assert q.intent == "procedure", f"Expected procedure, got {q.intent}"

    def test_intent_obligation(self):
        q = detect_topic("Society must maintain accounts?")
        assert q.intent == "obligation", f"Expected obligation, got {q.intent}"

    def test_intent_remedy(self):
        q = detect_topic("What can member do if committee refuses?")
        assert q.intent == "remedy", f"Expected remedy, got {q.intent}"

    def test_intent_clarification(self):
        q = detect_topic("What is quorum?")
        assert q.intent == "clarification", f"Expected clarification, got {q.intent}"

    def test_intent_rights(self):
        q = detect_topic("Do I have right to inspect accounts?")
        assert q.intent == "rights", f"Expected rights, got {q.intent}"


class TestActorExtraction:
    def test_actor_society(self):
        q = detect_topic("Can society appoint expert director?")
        assert q.actor == "society", f"Expected society, got {q.actor}"

    def test_actor_committee(self):
        q = detect_topic("Can committee remove secretary?")
        assert q.actor == "committee", f"Expected committee, got {q.actor}"

    def test_actor_member(self):
        q = detect_topic("Can member transfer shares?")
        assert q.actor == "member", f"Expected member, got {q.actor}"

    def test_actor_office_bearer(self):
        q = detect_topic("Can secretary call meeting?")
        assert q.actor == "office_bearer", f"Expected office_bearer, got {q.actor}"

    def test_actor_registrar(self):
        q = detect_topic("Can registrar appoint administrator?")
        assert q.actor == "registrar", f"Expected registrar, got {q.actor}"

    def test_actor_empty(self):
        q = detect_topic("What are the parking rules?")
        assert q.actor == "", f"Expected empty actor, got {q.actor}"


class TestActionExtraction:
    def test_action_appoint(self):
        q = detect_topic("Can society appoint expert director?")
        assert q.action == "appoint", f"Expected appoint, got {q.action}"

    def test_action_remove(self):
        q = detect_topic("Can committee remove secretary?")
        assert q.action == "remove", f"Expected remove, got {q.action}"

    def test_action_transfer(self):
        q = detect_topic("How to transfer share certificate?")
        assert q.action == "transfer", f"Expected transfer, got {q.action}"

    def test_action_recover(self):
        q = detect_topic("Can society recover dues from member?")
        assert q.action == "recover", f"Expected recover, got {q.action}"

    def test_action_hold(self):
        q = detect_topic("Can chairman hold AGM without notice?")
        assert q.action == "hold", f"Expected hold, got {q.action}"

    def test_action_vote(self):
        q = detect_topic("Who can vote in committee elections?")
        assert q.action == "vote", f"Expected vote, got {q.action}"


class TestSubjectExtraction:
    def test_subject_expert_director(self):
        q = detect_topic("Can society appoint expert director?")
        assert q.subject == "expert director", f"Expected expert director, got {q.subject}"

    def test_subject_secretary(self):
        q = detect_topic("Can committee remove secretary?")
        assert q.subject == "office bearer", f"Expected office bearer, got {q.subject}"

    def test_subject_quorum(self):
        q = detect_topic("What is quorum for AGM?")
        assert q.subject == "quorum", f"Expected quorum, got {q.subject}"

    def test_subject_maintenance_charges(self):
        q = detect_topic("Can society increase maintenance charges?")
        assert q.subject == "maintenance charges", f"Expected maintenance charges, got {q.subject}"

    def test_subject_parking_slot(self):
        q = detect_topic("Can committee allot parking slot?")
        assert q.subject == "parking slot", f"Expected parking slot, got {q.subject}"

    def test_subject_sinking_fund(self):
        q = detect_topic("How to use sinking fund for repairs?")
        assert q.subject == "sinking fund", f"Expected sinking fund, got {q.subject}"

    def test_subject_nominee(self):
        q = detect_topic("Can member change nominee?")
        assert q.subject == "nominee", f"Expected nominee, got {q.subject}"

    def test_subject_empty(self):
        q = detect_topic("What are the rules?")
        assert q.subject == "", f"Expected empty subject, got {q.subject}"


class TestSectionReferenceExtraction:
    def test_section_ref_detected(self):
        q = detect_topic("What does bye-law 25 say about parking?")
        assert q.section_ref == "25", f"Expected 25, got {q.section_ref}"

    def test_section_with_subsection(self):
        q = detect_topic("Bye-law 17(a) committee composition")
        assert q.section_ref == "17", f"Expected 17, got {q.section_ref}"
        assert q.subsection_ref == "a", f"Expected a, got {q.subsection_ref}"

    def test_section_ref_empty(self):
        q = detect_topic("Can committee remove secretary?")
        assert q.section_ref == "", f"Expected empty section ref, got {q.section_ref}"


class TestQueryInsightRoundtrip:
    def test_full_example_society_appoint_expert_director(self):
        q = detect_topic("Can society appoint expert director?")
        assert q.intent == "authority"
        assert q.actor == "society"
        assert q.action == "appoint"
        assert q.subject == "expert director"
        assert q.section_ref == ""

    def test_full_example_committee_remove_secretary(self):
        q = detect_topic("Can committee remove secretary?")
        assert q.intent == "authority"
        assert q.actor == "committee"
        assert q.action == "remove"
        assert q.subject == "office bearer"
        assert q.section_ref == ""

    def test_full_example_agm_quorum(self):
        q = detect_topic("What is quorum for AGM?")
        assert q.intent == "clarification"
        assert q.actor == ""
        assert q.action == ""
        assert q.subject == "quorum"
        assert q.topic == "agm"

    def test_general_query_no_extraction(self):
        q = detect_topic("What are the rules?")
        assert q.actor == ""
        assert q.action == ""
        assert q.subject == ""
        assert q.intent == "clarification"
