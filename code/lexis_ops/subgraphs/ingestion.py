import hashlib
from typing import Any, Dict
from lexis_ops.schemas.state import LexisOpsState
from lexis_ops.security.gate import PreLLMSecurityGate


def ingestion_security_node(state: LexisOpsState) -> Dict[str, Any]:
    """
    Ingestion & Pre-LLM Security Gate:
    1. Generates SHA-256 document content hash.
    2. Evaluates sealed case status & scans for unredacted SSN/juvenile PII.
    3. Blocks egress to downstream LLM components if violations exist.
    """
    raw_text = state.get("document_raw_text", "")
    is_sealed = state.get("is_sealed", False)
    case_type = state.get("case_type", "CIVIL")

    # Generate document hash
    doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # Pre-LLM Security Gate evaluation
    security_eval = PreLLMSecurityGate.evaluate(
        is_sealed=is_sealed,
        raw_text=raw_text,
        case_type=case_type,
    )

    if not security_eval.cleared:
        return {
            "doc_hash_sha256": doc_hash,
            "security_cleared": False,
            "security_violations": security_eval.pii_violations,
            "severity_level": "SEV-1",
            "requires_clerk_review": True,
            "workflow_status": "HALTED_SECURITY",
            "procedural_defects": [
                {
                    "rule_citation": "CJIS/FedRAMP Rule 5.9",
                    "defect_description": "; ".join(security_eval.pii_violations),
                    "severity": "EMERGENCY_HALT",
                    "page_reference": 1,
                }
            ],
        }

    return {
        "doc_hash_sha256": doc_hash,
        "security_cleared": True,
        "security_violations": [],
        "workflow_status": "INGESTED",
    }
