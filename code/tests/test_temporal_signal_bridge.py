from __future__ import annotations

import hmac
import hashlib
import time
import pytest

from lexis_ops.orchestration.temporal_workflow import (
    CLERK_SECRET_KEY,
    ClerkTokenValidator,
    LexisOpsFilingWorkflow,
    activity_ocr_ingress,
    activity_security_and_precheck,
)


def test_hmac_clerk_token_generation_and_cross_platform_verification():
    """Verifies that HMAC token generated with standard specifications passes verification."""
    clerk_id = "CLERK_USER_42"
    case_id = "2026-CV-004812"
    action = "APPROVE_OVERRIDE"
    ts = 1757000000

    # 1. Manual HMAC computation as done in Node.js
    msg = f"{clerk_id}:{case_id}:{action}:{ts}"
    expected_sig = hmac.new(CLERK_SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    node_token = f"{msg}:{expected_sig}"

    # 2. Verify with Python ClerkTokenValidator
    assert ClerkTokenValidator.verify_token(node_token) is True

    # 3. Verify Python validator generates identical token
    py_token = ClerkTokenValidator.generate_token(clerk_id, case_id, action, timestamp=ts)
    assert py_token == node_token


def test_hmac_clerk_token_rejection_on_tampered_payload():
    """Verifies that modifying action or case_id invalidates the token."""
    token = ClerkTokenValidator.generate_token("CLERK_USER_42", "2026-CV-004812", "APPROVE_OVERRIDE")
    assert ClerkTokenValidator.verify_token(token) is True

    # Tamper with action
    parts = token.split(":")
    tampered_parts = [parts[0], parts[1], "FORGED_ACTION", parts[3], parts[4]]
    tampered_token = ":".join(tampered_parts)

    assert ClerkTokenValidator.verify_token(tampered_token) is False


@pytest.mark.asyncio
async def test_live_workflow_signal_unblocks_wait_condition():
    """Verifies that submitting a valid signed signal unblocks the Temporal workflow suspension."""
    workflow = LexisOpsFilingWorkflow()

    # Pre-check suspends workflow
    workflow.workflow_status = "SUSPENDED_FOR_CLERK_REVIEW"
    workflow.review_queue_task = {"case_number": "2026-CV-009999", "severity": "SEV-2"}

    # Signal with invalid token is ignored
    workflow.submit_clerk_decision({
        "clerk_id": "CLERK_USER_42",
        "action": "APPROVE_OVERRIDE",
        "clerk_token": "FORGED_TOKEN_12345",
    })
    assert workflow.clerk_decision is None

    # Signal with verified HMAC token unblocks decision
    valid_token = ClerkTokenValidator.generate_token("CLERK_USER_42", "2026-CV-009999", "APPROVE_OVERRIDE")
    workflow.submit_clerk_decision({
        "clerk_id": "CLERK_USER_42",
        "action": "APPROVE_OVERRIDE",
        "clerk_token": valid_token,
        "notes": "Verified by review clerk",
    })

    assert workflow.clerk_decision is not None
    assert workflow.clerk_decision["override_authorized"] is True
    assert workflow.clerk_decision["token"] == valid_token
