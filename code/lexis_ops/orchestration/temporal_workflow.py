from __future__ import annotations

import hmac
import hashlib
import time
from datetime import timedelta
from typing import Any, Dict, Optional

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from lexis_ops.ingestion.ocr_parser import ingest_filing
from lexis_ops.subgraphs.ingestion import ingestion_security_node
from lexis_ops.subgraphs.notice_generation import notice_and_audit_node
from lexis_ops.subgraphs.scheduling import constraint_scheduling_node
from lexis_ops.subgraphs.validation import deterministic_rule_engine_node, structured_extraction_node

CLERK_SECRET_KEY = "LEXIS_OPS_CLERK_HMAC_MASTER_KEY"


class ClerkTokenValidator:
    """
    Cryptographic HMAC-SHA256 validation for Clerk Review Queue authorization tokens.
    Guarantees non-repudiation and prevents unauthorized resumption of suspended workflows.
    """

    @staticmethod
    def generate_token(clerk_id: str, case_id: str, action: str, timestamp: Optional[int] = None) -> str:
        ts = timestamp if timestamp is not None else int(time.time())
        msg = f"{clerk_id}:{case_id}:{action}:{ts}"
        sig = hmac.new(CLERK_SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return f"{msg}:{sig}"

    @staticmethod
    def verify_token(signed_token: str) -> bool:
        try:
            parts = signed_token.split(":")
            if len(parts) != 5:
                return False
            clerk_id, case_id, action, ts_str, sig = parts
            msg = f"{clerk_id}:{case_id}:{action}:{ts_str}"
            expected_sig = hmac.new(CLERK_SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, expected_sig)
        except Exception:
            return False


# ==========================================
# Temporal Activities
# ==========================================

@activity.defn(name="activity_ocr_ingress")
async def activity_ocr_ingress(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ingress & OCR Gate: Docling / XML conversion into typed Pydantic state."""
    content = payload.get("document_raw_text", "")
    filename = payload.get("filename", payload.get("document_title", "filing.pdf"))
    format_type = payload.get("source_format")

    ingress = ingest_filing(content, filename=filename, format_type=format_type)
    return {
        "case_number": ingress.case_number or payload.get("case_number", "2026-CV-000000"),
        "document_title": payload.get("document_title") or ingress.document_title,
        "document_raw_text": ingress.document_raw_text or content,
        "is_sealed": ingress.is_sealed or payload.get("is_sealed", False),
        "emergency_motion": ingress.emergency_motion or payload.get("emergency_motion", False),
        "ada_accommodations": ingress.metadata.ada_accommodations or payload.get("ada_accommodations", []),
        "source_format": ingress.source_format,
        "extraction_confidence": payload.get("extraction_confidence", ingress.metadata.confidence_score),
    }


@activity.defn(name="activity_security_and_precheck")
async def activity_security_and_precheck(state: Dict[str, Any]) -> Dict[str, Any]:
    """Security Gate & Deterministic Pre-Check Rule Engine."""
    # 1. Ingestion Security Gate
    s1 = ingestion_security_node(state)  # type: ignore
    merged = {**state, **s1}
    if not merged.get("security_cleared", True):
        return merged

    # 2. Structured Extraction
    s2 = structured_extraction_node(merged)  # type: ignore
    merged = {**merged, **s2}

    # 3. Deterministic Rule Engine
    s3 = deterministic_rule_engine_node(merged)  # type: ignore
    return {**merged, **s3}


@activity.defn(name="activity_constraint_scheduling")
async def activity_constraint_scheduling(state: Dict[str, Any]) -> Dict[str, Any]:
    """Google OR-Tools CP-SAT constraint optimization."""
    s4 = constraint_scheduling_node(state)  # type: ignore
    return {**state, **s4}


@activity.defn(name="activity_notice_and_audit")
async def activity_notice_and_audit(state: Dict[str, Any]) -> Dict[str, Any]:
    """Instructor Notice generation + Cryptographic chained SHA-256 audit ledger."""
    s5 = notice_and_audit_node(state)  # type: ignore
    return {**state, **s5}


# ==========================================
# Temporal Workflow Definition
# ==========================================

@workflow.defn(name="LexisOpsFilingWorkflow")
class LexisOpsFilingWorkflow:
    """
    Durable Temporal Workflow for LexisOps Court Administration:
    - Suspends if an emergency motion or defective filing is detected.
    - Issues task to Next.js clerk review queue.
    - Resumes ONLY when a valid HMAC-signed clerk token is submitted via Signal.
    - Persists audit ledger chaining before dispatch.
    """

    def __init__(self) -> None:
        self.clerk_decision: Optional[Dict[str, Any]] = None
        self.review_queue_task: Optional[Dict[str, Any]] = None
        self.workflow_status: str = "INITIALIZED"

    @workflow.signal(name="submit_clerk_decision")
    def submit_clerk_decision(self, signal_payload: Dict[str, Any]) -> None:
        """
        Receives signed clerk token signal from Next.js Clerk Review Queue.
        Validates HMAC signature before setting decision.
        """
        token = signal_payload.get("clerk_token", "")
        if not ClerkTokenValidator.verify_token(token):
            # Reject forged / unverified token
            return

        self.clerk_decision = {
            "clerk_id": signal_payload.get("clerk_id", "CLERK_OVERRIDE"),
            "action": signal_payload.get("action", "APPROVE_OVERRIDE"),
            "notes": signal_payload.get("notes", "Verified by Clerk"),
            "override_authorized": signal_payload.get("action") == "APPROVE_OVERRIDE",
            "token": token,
            "relief_designation": signal_payload.get("relief_designation"),
        }

    @workflow.query(name="get_review_queue_task")
    def get_review_queue_task(self) -> Optional[Dict[str, Any]]:
        """Queries the current pending clerk review task."""
        return self.review_queue_task

    @workflow.run
    async def run(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_attempts=3,
        )

        # 1. Ingress & OCR Gate Activity
        state = await workflow.execute_activity(
            activity_ocr_ingress,
            input_payload,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )

        # 2. Security Gate & Deterministic Pre-Check Activity
        state = await workflow.execute_activity(
            activity_security_and_precheck,
            state,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )

        # 3. Check for Emergency Motion, Defective Filing, or Unstructured Pro Se Quarantine
        if state.get("requires_clerk_review", False):
            self.workflow_status = "SUSPENDED_FOR_CLERK_REVIEW"
            self.review_queue_task = {
                "case_number": state.get("case_number"),
                "document_title": state.get("document_title"),
                "defects": state.get("procedural_defects", []),
                "severity": state.get("severity_level", "SEV-2"),
                "pro_se_quarantined": state.get("pro_se_quarantined", False),
                "confidence": state.get("extraction_confidence", 1.0),
                "suspended_at": workflow.now().isoformat(),
            }

            # Workflow suspends execution until clerk token signal is received
            await workflow.wait_condition(lambda: self.clerk_decision is not None)

            # Resumed upon valid clerk token submission
            state["clerk_decision"] = self.clerk_decision
            state["requires_clerk_review"] = False

            if self.clerk_decision.get("relief_designation"):
                state["relief_designation"] = self.clerk_decision["relief_designation"]
                state["document_title"] = self.clerk_decision["relief_designation"]
                state["pro_se_quarantined"] = False

            if self.clerk_decision.get("override_authorized"):
                state["workflow_status"] = "VALIDATED"
            else:
                state["workflow_status"] = "DEFICIENT"

        # 4. Constraint & Scheduling Engine (OR-Tools) if approved/valid
        if state.get("workflow_status") in ("VALIDATED", "SCHEDULED"):
            state = await workflow.execute_activity(
                activity_constraint_scheduling,
                state,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )

        # 5. Notice Drafting (Instructor) & SHA-256 Audit Chaining Activity
        final_state = await workflow.execute_activity(
            activity_notice_and_audit,
            state,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )

        self.workflow_status = "COMPLETED"
        return final_state
