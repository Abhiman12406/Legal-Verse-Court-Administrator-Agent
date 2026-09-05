from __future__ import annotations

import pytest
from lexis_ops.schemas.state import LexisOpsState
from lexis_ops.subgraphs.validation import deterministic_rule_engine_node
from lexis_ops.subgraphs.notice_generation import notice_and_audit_node
from lexis_ops.orchestration.temporal_workflow import (
    LexisOpsFilingWorkflow,
    ClerkTokenValidator,
)


def test_ingress_confidence_below_threshold_triggers_sev3_quarantine():
    """Verifies that an unstructured pro se pleading with extraction confidence < 0.70 triggers SEV-3 quarantine."""
    state: LexisOpsState = {
        "case_id": "c500-2026-cv-003418",
        "case_number": "2026-CV-003418",
        "filing_party_type": "PRO_SE",
        "document_title": "HANDWRITTEN NOTE REGARDING EVICTION AND FEES",
        "is_emergency": False,
        "signature_detected": True,
        "certificate_of_service_valid": False,
        "extraction_confidence": 0.64,
        "workflow_status": "VALIDATING",
        "procedural_defects": [],
        "pro_se_quarantined": False,
    }

    result = deterministic_rule_engine_node(state)

    assert result["pro_se_quarantined"] is True
    assert result["severity_level"] == "SEV-3: UNSTRUCTURED_PRO_SE"
    assert result["requires_clerk_review"] is True
    assert result["workflow_status"] == "AWAITING_CLERK"

    # Verify rule citation cites Administrative Directive 2026-04(b)
    directive_defects = [
        d for d in result["procedural_defects"]
        if d.get("rule_citation") == "Administrative Directive 2026-04(b)"
    ]
    assert len(directive_defects) == 1
    assert "Unstructured Pro Se Pleading" in directive_defects[0]["defect_description"]
    assert "Administrative Directive 2026-04(b)" in directive_defects[0]["rule_citation"]


def test_ingress_confidence_above_threshold_does_not_quarantine():
    """Verifies that a well-structured pro se pleading with confidence >= 0.75 does not trigger SEV-3 quarantine."""
    state: LexisOpsState = {
        "case_id": "c200-2026-cv-887711",
        "case_number": "2026-CV-887711",
        "filing_party_type": "PRO_SE",
        "document_title": "EMERGENCY EX PARTE MOTION FOR STAY OF WRIT",
        "is_emergency": True,
        "signature_detected": True,
        "certificate_of_service_valid": True,
        "extraction_confidence": 0.88,
        "workflow_status": "VALIDATING",
        "procedural_defects": [],
        "pro_se_quarantined": False,
    }

    result = deterministic_rule_engine_node(state)

    assert result.get("pro_se_quarantined") is False
    assert result.get("severity_level") != "SEV-3: UNSTRUCTURED_PRO_SE"


def test_notice_generation_suspended_when_pro_se_quarantined_without_relief_designation():
    """Verifies notice generation is halted for quarantined filings to prevent premature defaults or hallucinated citations."""
    state: LexisOpsState = {
        "case_id": "c500-2026-cv-003418",
        "case_number": "2026-CV-003418",
        "document_title": "UNCLASSIFIED PRO SE SUBMISSION",
        "filing_party_type": "PRO_SE",
        "workflow_status": "AWAITING_CLERK",
        "severity_level": "SEV-3: UNSTRUCTURED_PRO_SE",
        "pro_se_quarantined": True,
        "relief_designation": None,
        "procedural_defects": [],
        "generated_notices": [],
        "audit_trail": [],
        "clerk_decision": None,
    }

    result = notice_and_audit_node(state)

    # Notice list remains empty because notice generation was suspended
    assert len(result["generated_notices"]) == 0

    # Audit trail records the quarantine suspension event
    audit_trail = result["audit_trail"]
    assert len(audit_trail) >= 1
    assert audit_trail[-1]["event_type"] == "NOTICE_GENERATION_SUSPENDED_FOR_CLERK_CLASSIFICATION"


def test_temporal_workflow_pro_se_signal_with_relief_designation():
    """Verifies the live signal handler accepts relief_designation and records verified metadata."""
    workflow = LexisOpsFilingWorkflow()
    case_num = "2026-CV-003418"

    workflow.workflow_status = "SUSPENDED_FOR_CLERK_REVIEW"
    workflow.review_queue_task = {
        "case_number": case_num,
        "severity": "SEV-3: UNSTRUCTURED_PRO_SE",
        "pro_se_quarantined": True,
        "confidence": 0.64,
    }

    token = ClerkTokenValidator.generate_token("CLERK_USER_42", case_num, "APPROVE_OVERRIDE")
    relief_title = "Petition for In Forma Pauperis (Fee Waiver)"

    workflow.submit_clerk_decision({
        "clerk_id": "CLERK_USER_42",
        "action": "APPROVE_OVERRIDE",
        "clerk_token": token,
        "notes": "Verified indigent affidavit attached.",
        "relief_designation": relief_title,
    })

    assert workflow.clerk_decision is not None
    assert workflow.clerk_decision["override_authorized"] is True
    assert workflow.clerk_decision["relief_designation"] == relief_title
    assert workflow.clerk_decision["token"] == token


def test_notice_generation_after_clerk_relief_designation():
    """Verifies that once the clerk assigns a relief designation and schedules, plain-language notice is generated."""
    relief_title = "Petition for In Forma Pauperis (Fee Waiver)"
    state: LexisOpsState = {
        "case_id": "c500-2026-cv-003418",
        "case_number": "2026-CV-003418",
        "document_title": relief_title,
        "filing_party_type": "PRO_SE",
        "workflow_status": "SCHEDULED",
        "pro_se_quarantined": False,
        "relief_designation": relief_title,
        "procedural_defects": [],
        "generated_notices": [],
        "audit_trail": [],
        "scheduled_slot": {
            "hearing_id": "slot-test-01",
            "case_number": "2026-CV-003418",
            "courtroom_id": "CR-101",
            "assigned_judge_id": "HON. SARAH LIN",
            "scheduled_date": "2026-09-30",
            "start_time": "10:00:00",
            "duration_minutes": 45,
            "interpreter_locked": True,
            "status": "CONFIRMED",
        },
        "clerk_decision": {
            "action": "APPROVE_OVERRIDE",
            "clerk_id": "CLERK_USER_42",
            "decision_notes": "Oral verification and indigent schedule reviewed.",
            "relief_designation": relief_title,
        },
    }

    result = notice_and_audit_node(state)

    assert len(result["generated_notices"]) == 1
    notice = result["generated_notices"][0]
    assert notice["notice_type"] == "NOTICE_OF_HEARING"
    assert relief_title in notice["body_text"]
    assert "CR-101" in notice["body_text"]
    assert "HON. SARAH LIN" in notice["body_text"]
    assert result["audit_trail"][-1]["event_type"] == "HEARING_SCHEDULED_NOTICE_ISSUED"


def test_end_to_end_unstructured_pro_se_ingress_quarantine_to_resolution():
    """
    Complete end-to-end test:
    1. Raw messy pro se text is ingested via ingest_filing (caption missing / low confidence).
    2. Extraction & Rule Engine flags filing as SEV-3: UNSTRUCTURED_PRO_SE with pro_se_quarantined=True.
    3. Notice generation is suspended (0 notices, audit event logged).
    4. Clerk submits HMAC token with relief designation over signal bridge.
    5. Notice generation resumes with verified relief title and plain-language notice.
    """
    from lexis_ops.ingestion.ocr_parser import ingest_filing
    from lexis_ops.subgraphs.extraction import DeterministicMockAdapter
    from lexis_ops.subgraphs.validation import set_default_extraction_adapter, structured_extraction_node

    set_default_extraction_adapter(DeterministicMockAdapter())

    raw_pleading = (
        "TO THE CLERK:\n"
        "I am writing because I cannot pay the filing fees. I am disabled and have no income.\n"
        "Please stop the landlord from evicting me. I need Spanish interpreter at court.\n"
        "/s/ Carlos Gomez\n"
        "Defendant Pro Se"
    )

    # 1. Ingress
    ingress = ingest_filing(raw_pleading, filename="informal_note.txt")
    assert ingress.metadata.confidence_score < 0.70

    # 2. Structured Extraction & Rule Engine
    state: LexisOpsState = {
        "case_id": "c500-2026-cv-003418",
        "case_number": "UNKNOWN-CASE-NO",
        "document_raw_text": raw_pleading,
        "extraction_confidence": ingress.metadata.confidence_score,
        "document_title": ingress.document_title,
    }

    extracted = structured_extraction_node(state)
    merged_state = {**state, **extracted}
    rule_results = deterministic_rule_engine_node(merged_state)
    full_state = {**merged_state, **rule_results}

    assert full_state["extraction_confidence"] < 0.70
    assert full_state["pro_se_quarantined"] is True
    assert full_state["severity_level"] == "SEV-3: UNSTRUCTURED_PRO_SE"
    assert full_state["workflow_status"] == "AWAITING_CLERK"

    # 3. Notice generation suspended
    suspended_result = notice_and_audit_node(full_state)
    assert len(suspended_result["generated_notices"]) == 0
    assert suspended_result["audit_trail"][-1]["event_type"] == "NOTICE_GENERATION_SUSPENDED_FOR_CLERK_CLASSIFICATION"

    # 4. Clerk submits relief designation via HMAC token
    case_num = "2026-CV-003418"
    token = ClerkTokenValidator.generate_token("CLERK_USER_42", case_num, "APPROVE_OVERRIDE")
    relief_choice = "Emergency Motion for Stay of Eviction / Writ"

    workflow = LexisOpsFilingWorkflow()
    workflow.workflow_status = "SUSPENDED_FOR_CLERK_REVIEW"
    workflow.submit_clerk_decision({
        "clerk_id": "CLERK_USER_42",
        "action": "APPROVE_OVERRIDE",
        "clerk_token": token,
        "notes": "Verified emergency ex parte stay request.",
        "relief_designation": relief_choice,
    })

    assert workflow.clerk_decision["relief_designation"] == relief_choice
    assert workflow.clerk_decision["token"] == token

    # 5. Workflow resumes with verified classification metadata
    resumed_state: LexisOpsState = {
        **full_state,
        "case_number": case_num,
        "workflow_status": "SCHEDULED",
        "pro_se_quarantined": False,
        "relief_designation": relief_choice,
        "document_title": relief_choice,
        "clerk_decision": workflow.clerk_decision,
        "scheduled_slot": {
            "hearing_id": "slot-pro-se-01",
            "case_number": case_num,
            "courtroom_id": "CR-101",
            "assigned_judge_id": "HON. SARAH LIN",
            "scheduled_date": "2026-09-08",
            "start_time": "09:30:00",
            "duration_minutes": 30,
            "interpreter_locked": True,
            "status": "CONFIRMED",
        },
    }

    final_result = notice_and_audit_node(resumed_state)
    assert len(final_result["generated_notices"]) == 1
    notice = final_result["generated_notices"][0]
    assert notice["notice_type"] == "NOTICE_OF_HEARING"
    assert relief_choice in notice["body_text"]
    assert "CR-101" in notice["body_text"]
    assert final_result["audit_trail"][-1]["event_type"] == "HEARING_SCHEDULED_NOTICE_ISSUED"

