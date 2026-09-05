from __future__ import annotations

from typing import Any, Dict
from langgraph.types import interrupt
from lexis_ops.schemas.state import (
    ClerkActionType,
    ClerkDecision,
    ClerkExceptionCard,
    LexisOpsState,
    ProceduralDefect,
)


def clerk_escalation_node(state: LexisOpsState) -> Dict[str, Any]:
    """
    Human-in-the-Loop Clerk Review & Escalation Node.
    Uses native LangGraph interrupt() to suspend execution when defects,
    emergencies, or low confidence are flagged.
    Execution resumes when the clerk submits an action payload.
    """
    defects_data = state.get("procedural_defects", [])
    defects = [ProceduralDefect(**d) for d in defects_data]
    case_number = state.get("case_number", "UNKNOWN")
    severity = state.get("severity_level", "SEV-2")
    is_emergency = state.get("is_emergency", False)

    summary = (
        f"EMERGENCY PRIORITY REVIEW ({severity}): Immediate Judicial Action Required."
        if is_emergency
        else f"Procedural Review ({severity}): {len(defects)} defect(s) detected. Awaiting clerk authorization."
    )

    card = ClerkExceptionCard(
        case_number=case_number,
        document_title=state.get("document_title", "General Filing"),
        severity_level=severity,
        defects=defects,
        confidence=state.get("extraction_confidence", 1.0),
        is_emergency=is_emergency,
        summary_message=summary,
    )

    # Halt execution thread and surface card to Clerk Dashboard
    raw_response = interrupt(card.model_dump())

    # Execution resumes here when Command(resume=payload) is sent by clerk UI
    clerk_decision: Dict[str, Any]
    if isinstance(raw_response, dict):
        clerk_decision = raw_response
    else:
        clerk_decision = {
            "action": str(raw_response),
            "clerk_id": "CLERK_DEFAULT",
            "decision_notes": "Resumed from interruption",
        }

    action_str = clerk_decision.get("action", ClerkActionType.APPROVE_OVERRIDE.value)

    if action_str == ClerkActionType.APPROVE_OVERRIDE.value:
        return {
            "clerk_decision": clerk_decision,
            "requires_clerk_review": False,
            "workflow_status": "VALIDATED",
        }
    elif action_str == ClerkActionType.ISSUE_DEFICIENCY.value:
        return {
            "clerk_decision": clerk_decision,
            "requires_clerk_review": False,
            "workflow_status": "DEFICIENT",
        }
    elif action_str == ClerkActionType.REASSIGN_JUDGE.value:
        return {
            "clerk_decision": clerk_decision,
            "requires_clerk_review": False,
            "workflow_status": "REASSIGNED",
        }
    else:
        return {
            "clerk_decision": clerk_decision,
            "requires_clerk_review": False,
            "workflow_status": "AWAITING_CLERK",
        }
