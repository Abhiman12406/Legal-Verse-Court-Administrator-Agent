from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from lexis_ops.schemas.state import LexisOpsState
from lexis_ops.security.audit_ledger import CryptographicAuditLedger
from lexis_ops.subgraphs.instructor_notices import (
    DeficiencyCureNoticeSchema,
    DiscretionaryHearingNoticeSchema,
    InstructorNoticeGenerator,
)


def render_notice_template(notice_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renders standardized judicial council notice templates.
    Strictly deterministic assembly with zero LLM prose generation (PRD FR-NOTIF-01).
    """
    timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if notice_type == "NOTICE_OF_HEARING":
        slot = context.get("scheduled_slot", {})
        body = (
            f"IN THE TRIAL COURT OF THE JUDICIAL DISTRICT\n\n"
            f"CASE NO: {context.get('case_number')}\n"
            f"DATE: {timestamp}\n\n"
            f"FORMAL NOTICE OF HEARING\n\n"
            f"PLEASE TAKE NOTICE that a hearing on '{context.get('document_title', 'Motion')}' "
            f"has been calendarized before the Honorable {slot.get('assigned_judge_id', 'Assigned Judge')}.\n\n"
            f"  • Scheduled Date: {slot.get('scheduled_date')}\n"
            f"  • Start Time: {slot.get('start_time')} Local Time\n"
            f"  • Courtroom: {slot.get('courtroom_id')}\n"
            f"  • Certified Accommodations Locked: {slot.get('interpreter_locked')}\n\n"
            f"Failure to appear may result in submission on papers or default ruling.\n"
            f"BY ORDER OF THE COURT.\n"
        )
        return {
            "notice_type": "NOTICE_OF_HEARING",
            "title": f"Notice of Hearing - {context.get('case_number')}",
            "body_text": body,
            "statutory_cure_days": None,
        }

    elif notice_type == "NOTICE_OF_DEFICIENCY":
        defects = context.get("procedural_defects", [])
        citations_block = "\n".join(
            f"  [{i+1}] {d.get('rule_citation')}: {d.get('defect_description')}"
            for i, d in enumerate(defects)
        )
        body = (
            f"IN THE TRIAL COURT OF THE JUDICIAL DISTRICT\n\n"
            f"CASE NO: {context.get('case_number')}\n"
            f"DATE: {timestamp}\n\n"
            f"NOTICE OF PROCEDURAL DEFICIENCY / INCOMPLETE FILING\n\n"
            f"The submission entitled '{context.get('document_title', 'Filing')}' has been evaluated "
            f"and deemed PROCEDURALLY DEFICIENT pursuant to Local Rules of Court.\n\n"
            f"SPECIFIC PROCEDURAL DEFICIENCIES CITED:\n"
            f"{citations_block}\n\n"
            f"TIME TO CURE: Pursuant to Local Rule 5.4, the filing party is granted FOURTEEN (14) DAYS "
            f"from the date of this notice to file an Amended Submission curing all stated defects.\n\n"
            f"CLERK OF COURT / AUTOMATED DOCKET GATEWAY\n"
        )
        return {
            "notice_type": "NOTICE_OF_DEFICIENCY",
            "title": f"Notice of Procedural Deficiency - {context.get('case_number')}",
            "body_text": body,
            "statutory_cure_days": 14,
        }

    else:
        body = (
            f"ADMINISTRATIVE NOTICE - CASE NO: {context.get('case_number')}\n"
            f"Event Status: {context.get('workflow_status')}\n"
            f"Date: {timestamp}\n"
        )
        return {
            "notice_type": "GENERAL_ADMINISTRATIVE_NOTICE",
            "title": f"Administrative Status Notice - {context.get('case_number')}",
            "body_text": body,
            "statutory_cure_days": None,
        }


def notice_and_audit_node(state: LexisOpsState) -> Dict[str, Any]:
    """
    Renders formal judicial council notices and appends a cryptographically
    chained SHA-256 audit record to the ledger.
    """
    status = state.get("workflow_status", "VALIDATED")
    case_id = state.get("case_id", "00000000-0000-0000-0000-000000000000")
    filing_id = state.get("doc_hash_sha256", "UNKNOWN_FILING")[:16]
    notices: List[Dict[str, Any]] = list(state.get("generated_notices", []))
    audit_trail: List[Dict[str, Any]] = list(state.get("audit_trail", []))
    latest_hash = state.get("latest_audit_hash") or CryptographicAuditLedger.GENESIS_HASH

    effective_title = state.get("relief_designation") or state.get("document_title", "Filing")

    # 1. Check if Notice Generation is Suspended (e.g. Awaiting Clerk Review or Pro Se Quarantine)
    if status == "AWAITING_CLERK" or (state.get("pro_se_quarantined", False) and not state.get("clerk_decision")):
        # Automated notice generation is suspended to avoid hallucinated citations or premature rulings
        event_type = "NOTICE_GENERATION_SUSPENDED_FOR_CLERK_CLASSIFICATION"
    elif status == "SCHEDULED":
        notice_context = {**state, "document_title": effective_title}
        notice = render_notice_template("NOTICE_OF_HEARING", notice_context)
        slot = state.get("scheduled_slot", {})
        structured_hearing = InstructorNoticeGenerator.generate_hearing_notice(
            case_number=state.get("case_number", "2026-CV-000000"),
            hearing_type=effective_title,
            assigned_judge=slot.get("assigned_judge_id", "Honorable Presiding Judge"),
            courtroom=slot.get("courtroom_id", "Courtroom 4A"),
            scheduled_date=slot.get("scheduled_date", "TBD"),
            start_time=slot.get("start_time", "09:00 AM"),
            accommodations=state.get("ada_accommodations", []),
        )
        notice["structured_schema"] = structured_hearing.model_dump()
        notices.append(notice)
        event_type = "HEARING_SCHEDULED_NOTICE_ISSUED"
    elif status in ("DEFICIENT", "HALTED_SECURITY"):
        notice_context = {**state, "document_title": effective_title}
        notice = render_notice_template("NOTICE_OF_DEFICIENCY", notice_context)
        structured_cure = InstructorNoticeGenerator.generate_deficiency_cure_notice(
            case_number=state.get("case_number", "2026-CV-000000"),
            document_title=effective_title,
            defects=state.get("procedural_defects", []),
        )
        notice["structured_schema"] = structured_cure.model_dump()
        notices.append(notice)
        event_type = "DEFICIENCY_NOTICE_ISSUED"
    elif status == "REASSIGNED":
        notice = render_notice_template("GENERAL_ADMINISTRATIVE_NOTICE", state)
        notices.append(notice)
        event_type = "JUDICIAL_REASSIGNMENT_ISSUED"
    else:
        event_type = "FILING_VALIDATED_DOCKETED"

    # 2. Commit cryptographically chained audit ledger record
    entry_id = len(audit_trail) + 1
    operator_id = (
        state.get("clerk_decision", {}).get("clerk_id", "SYSTEM_AGENT")
        if state.get("clerk_decision")
        else "SYSTEM_AGENT"
    )

    decision_payload = {
        "workflow_status": status,
        "severity_level": state.get("severity_level", "CLEAN"),
        "defects_count": len(state.get("procedural_defects", [])),
        "scheduled_slot": state.get("scheduled_slot"),
        "notices_generated": len(notices),
    }

    audit_entry = CryptographicAuditLedger.record_event(
        case_id=case_id,
        filing_id=filing_id,
        event_type=event_type,
        operator_id=operator_id,
        decision_payload=decision_payload,
        previous_hash=latest_hash,
        entry_id=entry_id,
    )

    audit_trail.append(audit_entry.model_dump())

    return {
        "generated_notices": notices,
        "audit_trail": audit_trail,
        "latest_audit_hash": audit_entry.current_hash,
        "workflow_status": "COMPLETED",
    }
