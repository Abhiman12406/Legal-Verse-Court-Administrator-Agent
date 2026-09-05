from __future__ import annotations

import pytest
import asyncio
from typing import Any, Dict

from lexis_ops.ingestion.ocr_parser import (
    DoclingPDFParser,
    DocketXMLParser,
    IngressFilingPayload,
    ingest_filing,
)
from lexis_ops.orchestration.temporal_workflow import (
    ClerkTokenValidator,
    LexisOpsFilingWorkflow,
    activity_ocr_ingress,
    activity_security_and_precheck,
    activity_constraint_scheduling,
    activity_notice_and_audit,
)
from lexis_ops.schemas.state import LexisOpsState
from lexis_ops.security.audit_ledger import CryptographicAuditLedger
from lexis_ops.subgraphs.instructor_notices import (
    DeficiencyCureNoticeSchema,
    DiscretionaryHearingNoticeSchema,
    InstructorNoticeGenerator,
)
from lexis_ops.subgraphs.scheduling import constraint_scheduling_node
from lexis_ops.subgraphs.validation import deterministic_rule_engine_node


# =========================================================================
# STEP 1: Ingress & OCR Gate (PDF filings & Docket XML to typed Pydantic)
# =========================================================================

def test_step1_ingress_docket_xml_to_pydantic():
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <CourtDocketFiling>
        <CaseNumber>2026-CV-004812</CaseNumber>
        <DocumentTitle>Motion for Summary Judgment</DocumentTitle>
        <FilingParty>Jane Doe</FilingParty>
        <SignatureBlock>/s/ Sarah Jenkins, Esq.</SignatureBlock>
        <CertificateOfService>Served via ECF on 2026-09-01</CertificateOfService>
        <FeeReceipt>Receipt #98234-TX</FeeReceipt>
        <DocumentText>Defendant requests an ASL interpreter for all hearing proceedings.</DocumentText>
    </CourtDocketFiling>
    """
    payload = DocketXMLParser.parse(xml_sample)
    assert isinstance(payload, IngressFilingPayload)
    assert payload.case_number == "2026-CV-004812"
    assert payload.document_title == "Motion for Summary Judgment"
    assert payload.source_format == "XML"
    assert payload.metadata.has_signature is True
    assert payload.metadata.has_certificate_of_service is True
    assert payload.metadata.has_fee_receipt is True
    assert "ASL_INTERPRETER" in payload.metadata.ada_accommodations


def test_step1_ingress_pdf_to_pydantic():
    legal_text_pdf_sim = """
    IN THE SUPERIOR COURT OF CALIFORNIA
    COUNTY OF LOS ANGELES

    CASE NO: 2026-CV-009941
    
    MOTION FOR PROTECTIVE ORDER UNDER SEAL
    
    Counsel respectfully requests an expedited hearing with Spanish interpreter.
    
    Respectfully submitted,
    /s/ Robert Vance, Esq.
    
    CERTIFICATE OF SERVICE
    I hereby certify that a true and correct copy was served.
    """
    payload = DoclingPDFParser.parse_pdf(legal_text_pdf_sim, filename="Motion_Protective_Order.pdf")
    assert isinstance(payload, IngressFilingPayload)
    assert payload.case_number == "2026-CV-009941"
    assert payload.metadata.has_signature is True
    assert payload.metadata.has_certificate_of_service is True
    assert payload.is_sealed is True
    assert "SPANISH_INTERPRETER" in payload.metadata.ada_accommodations


# =========================================================================
# STEP 2: Deterministic Pre-Check (Rule Engine scans baseline requirements)
# =========================================================================

def test_step2_deterministic_precheck_invalid_case_halts_immediately():
    state: LexisOpsState = {
        "case_number": "INVALID-1234",  # Fails regex ^\d{4}-[A-Z]{2}-\d{5,6}$
        "document_title": "Emergency Motion to Stay",
        "has_signature_block": True,
        "signature_detected": True,
        "has_certificate_of_service": True,
        "certificate_of_service_valid": True,
        "has_fee_receipt": True,
        "procedural_defects": [],
        "workflow_status": "INGESTED",
    }
    result = deterministic_rule_engine_node(state)
    assert result["requires_clerk_review"] is True
    assert result["workflow_status"] == "AWAITING_CLERK"
    assert any("Rule 3.1(a)" in d["rule_citation"] for d in result["procedural_defects"])


def test_step2_deterministic_precheck_missing_signature_and_cert():
    state: LexisOpsState = {
        "case_number": "2026-CV-001234",
        "document_title": "Motion in Limine",
        "signature_detected": False,
        "certificate_of_service_valid": False,
        "has_signature_block": False,
        "has_certificate_of_service": False,
        "has_fee_receipt": True,
        "procedural_defects": [],
        "workflow_status": "INGESTED",
    }
    result = deterministic_rule_engine_node(state)
    assert result["requires_clerk_review"] is True
    assert result["workflow_status"] == "AWAITING_CLERK"
    citations = [d["rule_citation"] for d in result["procedural_defects"]]
    assert any("Rule 11.1" in c for c in citations)
    assert any("Rule 5.2" in c for c in citations)


# =========================================================================
# STEP 3: Constraint & Schedule Engine (Google OR-Tools CP-SAT)
# =========================================================================

def test_step3_ortools_constraint_scheduling_advance_notice_and_ada():
    state: LexisOpsState = {
        "case_number": "2026-CV-004812",
        "document_title": "Motion to Compel Discovery",
        "assigned_judge_id": "JUDGE_MARTINEZ",
        "ada_accommodations": ["ASL_INTERPRETER"],
        "filing_date": "2026-09-01",
        "procedural_defects": [],
        "requires_clerk_review": False,
        "workflow_status": "VALIDATED",
    }
    result = constraint_scheduling_node(state)
    assert result["workflow_status"] == "SCHEDULED"
    slot = result["scheduled_slot"]
    assert slot is not None
    # Verify statutory advance notice buffer (minimum 21 days from filing date 2026-09-01 -> >= 2026-09-22)
    assert slot["scheduled_date"] >= "2026-09-22"
    # Verify ASL interpreter accommodation locked
    assert slot["interpreter_locked"] is True
    # Verify assigned to ADA/translation-equipped courtroom (CR-101 or CR-201)
    assert slot["courtroom_id"] in ["CR-101", "CR-201"]


# =========================================================================
# STEP 4: Constrained LLM Reasoning with Instructor Schemas
# =========================================================================

def test_step4_instructor_forced_strict_json_schemas():
    # 1. Deficiency Cure Notice Schema
    defects = [
        {"rule_citation": "FRCP Rule 11", "defect_description": "Omission of mandatory signature block"},
        {"rule_citation": "Local Rule 5.2", "defect_description": "Missing Certificate of Service"},
    ]
    notice = InstructorNoticeGenerator.generate_deficiency_cure_notice(
        case_number="2026-CV-004812",
        document_title="Motion to Dismiss",
        defects=defects,
    )
    assert isinstance(notice, DeficiencyCureNoticeSchema)
    assert notice.case_number == "2026-CV-004812"
    assert len(notice.deficiencies) == 2
    assert notice.statutory_cure_days == 14
    # Ensure constitutional boundary: purely procedural directions, zero legal advice
    assert "dismissal without prejudice" in notice.discretionary_instructions or "fourteen" in notice.discretionary_instructions

    # 2. Hearing Notice Schema
    hearing = InstructorNoticeGenerator.generate_hearing_notice(
        case_number="2026-CV-004812",
        hearing_type="Motion to Compel Discovery",
        assigned_judge="JUDGE_MARTINEZ",
        courtroom="CR-101",
        scheduled_date="2026-09-29",
        start_time="10:00 AM",
        accommodations=["ASL_INTERPRETER"],
    )
    assert isinstance(hearing, DiscretionaryHearingNoticeSchema)
    assert "ASL_INTERPRETER" in hearing.ada_accommodations_locked
    assert any("ASL interpreter" in p for p in hearing.procedural_instructions)


# =========================================================================
# STEP 5: Durable Orchestration (Temporal Workflow Suspension & Resumption)
# =========================================================================

def test_step5_clerk_hmac_token_validation():
    # Valid signed token
    token = ClerkTokenValidator.generate_token("CLERK_USER_42", "case-99", "APPROVE_OVERRIDE")
    assert ClerkTokenValidator.verify_token(token) is True

    # Tampered token fails verification
    tampered_token = token[:-4] + "ffff"
    assert ClerkTokenValidator.verify_token(tampered_token) is False


@pytest.mark.asyncio
async def test_step5_temporal_workflow_suspends_and_resumes_on_signed_clerk_token():
    workflow_instance = LexisOpsFilingWorkflow()

    # Input payload containing procedural defect (missing signature)
    input_payload = {
        "case_number": "2026-CV-007788",
        "document_title": "Emergency Motion for Stay",
        "document_raw_text": "Emergency motion without signature block.",
        "emergency_motion": True,
        "source_format": "PLAINTEXT",
    }

    # Execute Activity 1: OCR Ingress
    ingress_state = await activity_ocr_ingress(input_payload)
    assert ingress_state["document_title"] == "Emergency Motion for Stay"

    # Execute Activity 2: Pre-check (will detect missing signature & emergency)
    precheck_state = await activity_security_and_precheck(ingress_state)
    assert precheck_state["requires_clerk_review"] is True
    assert precheck_state["workflow_status"] == "AWAITING_CLERK"

    # Workflow suspends and issues review queue task
    workflow_instance.review_queue_task = {
        "case_number": precheck_state["case_number"],
        "defects": precheck_state["procedural_defects"],
        "severity": precheck_state["severity_level"],
    }
    workflow_instance.workflow_status = "SUSPENDED_FOR_CLERK_REVIEW"
    assert workflow_instance.workflow_status == "SUSPENDED_FOR_CLERK_REVIEW"

    # Test forged token rejection
    workflow_instance.submit_clerk_decision({
        "clerk_id": "CLERK_MALICIOUS",
        "action": "APPROVE_OVERRIDE",
        "clerk_token": "MALICIOUS_FORGED_TOKEN",
    })
    # Should remain un-resumed
    assert workflow_instance.clerk_decision is None

    # Submit valid HMAC signed clerk token
    valid_token = ClerkTokenValidator.generate_token("CLERK_USER_42", "2026-CV-007788", "APPROVE_OVERRIDE")
    workflow_instance.submit_clerk_decision({
        "clerk_id": "CLERK_USER_42",
        "action": "APPROVE_OVERRIDE",
        "clerk_token": valid_token,
    })
    assert workflow_instance.clerk_decision is not None
    assert workflow_instance.clerk_decision["override_authorized"] is True

    # Resumed state advances to scheduling & notice audit
    resumed_state = {
        **precheck_state,
        "clerk_decision": workflow_instance.clerk_decision,
        "requires_clerk_review": False,
        "workflow_status": "VALIDATED",
        "filing_date": "2026-09-01",
    }
    scheduled_state = await activity_constraint_scheduling(resumed_state)
    assert scheduled_state["workflow_status"] == "SCHEDULED"

    final_state = await activity_notice_and_audit(scheduled_state)
    assert final_state["workflow_status"] == "COMPLETED"
    assert len(final_state["generated_notices"]) > 0
    assert len(final_state["audit_trail"]) > 0


# =========================================================================
# STEP 6: Audit Chaining (Append-only SHA-256 ledger before notice dispatch)
# =========================================================================

def test_step6_cryptographic_audit_ledger_chaining_and_tamper_detection():
    ledger = []
    prev_hash = CryptographicAuditLedger.GENESIS_HASH

    # 1. Record Ingress & Precheck event
    e1 = CryptographicAuditLedger.record_event(
        case_id="case-101",
        filing_id="filing-101",
        event_type="INGRESS_AND_PRECHECK_COMPLETED",
        operator_id="SYSTEM_AGENT",
        decision_payload={"status": "VALIDATED", "defects_count": 0},
        previous_hash=prev_hash,
        entry_id=1,
    )
    ledger.append(e1)
    prev_hash = e1.current_hash

    # 2. Record Notice Dispatch event
    e2 = CryptographicAuditLedger.record_event(
        case_id="case-101",
        filing_id="filing-101",
        event_type="HEARING_SCHEDULED_NOTICE_ISSUED",
        operator_id="CLERK_USER_42",
        decision_payload={"courtroom": "CR-101", "scheduled_date": "2026-09-29"},
        previous_hash=prev_hash,
        entry_id=2,
    )
    ledger.append(e2)

    # Validate intact chain
    assert CryptographicAuditLedger.verify_chain(ledger) is True

    # Simulate tampering with event 1
    ledger[0].decision_payload["status"] = "TAMPERED_FRAUD"
    assert CryptographicAuditLedger.verify_chain(ledger) is False
