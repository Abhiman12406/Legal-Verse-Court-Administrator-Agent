from __future__ import annotations

from typing import Any, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from lexis_ops.schemas.state import LexisOpsState
from lexis_ops.subgraphs.extraction import ExtractionPort
from lexis_ops.subgraphs.hitl_escalation import clerk_escalation_node
from lexis_ops.subgraphs.ingestion import ingestion_security_node
from lexis_ops.subgraphs.notice_generation import notice_and_audit_node
from lexis_ops.subgraphs.scheduling import constraint_scheduling_node
from lexis_ops.subgraphs.validation import (
    deterministic_rule_engine_node,
    set_default_extraction_adapter,
    structured_extraction_node,
)


def route_post_ingestion(state: LexisOpsState) -> str:
    """Routes to clerk escalation if security gate triggered SEV-1, else to extraction."""
    if not state.get("security_cleared", True):
        return "clerk_escalation"
    return "structured_extraction"


def route_post_rule_engine(state: LexisOpsState) -> str:
    """Routes to clerk escalation if defects/emergencies exist, else to scheduling."""
    if state.get("requires_clerk_review", False):
        return "clerk_escalation"
    return "constraint_scheduling"


def route_post_clerk_escalation(state: LexisOpsState) -> str:
    """
    Routes based on clerk action:
    - If clerk approved override -> advance to scheduling
    - If clerk issued deficiency or reassignment -> proceed directly to notice & audit
    """
    status = state.get("workflow_status", "")
    if status == "VALIDATED":
        return "constraint_scheduling"
    return "notice_and_audit"


def route_post_scheduling(state: LexisOpsState) -> str:
    """Routes to clerk escalation if scheduling deadlock detected, else to notice & audit."""
    if state.get("requires_clerk_review", False):
        return "clerk_escalation"
    return "notice_and_audit"


def build_lexis_ops_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    default_extraction_adapter: Optional[ExtractionPort] = None,
):
    """
    Builds and compiles the hierarchical LexisOps StateGraph with checkpointer,
    extraction adapter seam, and native Human-in-the-Loop interrupt support.
    """
    if default_extraction_adapter is not None:
        set_default_extraction_adapter(default_extraction_adapter)

    workflow = StateGraph(LexisOpsState)

    # 1. Add Processing Nodes
    workflow.add_node("ingestion_security", ingestion_security_node)
    workflow.add_node("structured_extraction", structured_extraction_node)
    workflow.add_node("deterministic_rule_engine", deterministic_rule_engine_node)
    workflow.add_node("clerk_escalation", clerk_escalation_node)
    workflow.add_node("constraint_scheduling", constraint_scheduling_node)
    workflow.add_node("notice_and_audit", notice_and_audit_node)

    # 2. Wire Control Flow Edges
    workflow.add_edge(START, "ingestion_security")

    workflow.add_conditional_edges(
        "ingestion_security",
        route_post_ingestion,
        {
            "clerk_escalation": "clerk_escalation",
            "structured_extraction": "structured_extraction",
        },
    )

    workflow.add_edge("structured_extraction", "deterministic_rule_engine")

    workflow.add_conditional_edges(
        "deterministic_rule_engine",
        route_post_rule_engine,
        {
            "clerk_escalation": "clerk_escalation",
            "constraint_scheduling": "constraint_scheduling",
        },
    )

    workflow.add_conditional_edges(
        "clerk_escalation",
        route_post_clerk_escalation,
        {
            "constraint_scheduling": "constraint_scheduling",
            "notice_and_audit": "notice_and_audit",
        },
    )

    workflow.add_conditional_edges(
        "constraint_scheduling",
        route_post_scheduling,
        {
            "clerk_escalation": "clerk_escalation",
            "notice_and_audit": "notice_and_audit",
        },
    )

    workflow.add_edge("notice_and_audit", END)

    # Use provided checkpointer or default to MemorySaver for HITL interrupts
    saver = checkpointer if checkpointer is not None else MemorySaver()
    return workflow.compile(checkpointer=saver)
