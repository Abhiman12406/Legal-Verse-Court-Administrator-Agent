from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional
from langchain_core.runnables import RunnableConfig

from lexis_ops.schemas.state import (
    FilingPartyType,
    FilingValidationPayload,
    LexisOpsState,
    ProceduralDefect,
    ProceduralDefectSeverity,
)
from lexis_ops.subgraphs.extraction import (
    DeterministicMockAdapter,
    ExtractionPort,
    GeminiExtractionAdapter,
)

_DEFAULT_EXTRACTION_ADAPTER: Optional[ExtractionPort] = None


def set_default_extraction_adapter(adapter: Optional[ExtractionPort]) -> None:
    """Sets the global default extraction adapter for the process."""
    global _DEFAULT_EXTRACTION_ADAPTER
    _DEFAULT_EXTRACTION_ADAPTER = adapter


def structured_extraction_node(
    state: LexisOpsState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Tier 1: Constrained Metadata Extraction Node.
    Extracts purely factual structural components (case #, title, signature, service cert, emergency tags).
    Strictly barred from substantive legal evaluation (PRD Section 3.1).
    """
    adapter: Optional[ExtractionPort] = None
    if config and "configurable" in config:
        adapter = config["configurable"].get("extraction_adapter")

    if adapter is None:
        adapter = _DEFAULT_EXTRACTION_ADAPTER

    if adapter is None:
        # Default to Gemini in production (fails fast if no API key is configured)
        adapter = GeminiExtractionAdapter()

    raw_text = state.get("document_raw_text", "")
    payload = adapter.extract(raw_text)

    case_no = payload.case_number
    if state.get("case_number") and case_no == "UNKNOWN-CASE-NO":
        case_no = state["case_number"]

    confidence = payload.extraction_confidence
    if "extraction_confidence" in state and state["extraction_confidence"] is not None:
        try:
            confidence = min(confidence, float(state["extraction_confidence"]))
        except (ValueError, TypeError):
            pass

    return {
        "case_number": case_no,
        "document_title": payload.document_title,
        "filing_party_type": (
            payload.party_type.value
            if hasattr(payload.party_type, "value")
            else str(payload.party_type)
        ),
        "filing_date": payload.filing_date,
        "signature_detected": payload.signature_detected,
        "certificate_of_service_valid": payload.certificate_of_service_valid,
        "is_emergency": payload.is_emergency,
        "extraction_confidence": confidence,
    }


def deterministic_rule_engine_node(state: LexisOpsState) -> Dict[str, Any]:
    """
    Tier 2: Pure Deterministic Rule Engine Node.
    Evaluates extracted metadata against statutory deadlines and local rules:
    - Local Civil Rule 11 (Signature)
    - Local Civil Rule 5.2(b) (Certificate of Service)
    - Local Rule 3.1 (Case Number format)
    - SEV-1 Emergency Protocol
    """
    defects: List[Dict[str, Any]] = []
    case_number = state.get("case_number", "")
    signature_detected = state.get("signature_detected", False)
    cert_of_service_valid = state.get("certificate_of_service_valid", False)
    is_emergency = state.get("is_emergency", False)
    confidence = state.get("extraction_confidence", 1.0)

    # Rule 1: Signature Verification (Local Rule 11.1)
    if not signature_detected:
        defects.append(
            ProceduralDefect(
                rule_citation="Local Civil Rule 11.1",
                defect_description="Missing signature block: Filing lacks required wet-ink scan, cryptographic signature, or /s/ notation.",
                severity=ProceduralDefectSeverity.MANDATORY_REJECT,
                page_reference=state.get("page_count", 1),
            ).model_dump()
        )

    # Rule 2: Certificate of Service (Local Rule 5.2(b))
    if not cert_of_service_valid:
        defects.append(
            ProceduralDefect(
                rule_citation="Local Civil Rule 5.2(b)",
                defect_description="Missing Certificate of Service: Filings must verify delivery method and service addresses to all active parties.",
                severity=ProceduralDefectSeverity.MANDATORY_REJECT,
                page_reference=state.get("page_count", 1),
            ).model_dump()
        )

    # Rule 3: Case Number Format Check (FR-DOC-03)
    if not re.match(r"^\d{4}-[A-Z]{2}-\d{5,6}$", case_number):
        defects.append(
            ProceduralDefect(
                rule_citation="Local Rule 3.1(a)",
                defect_description=f"Caption Defect: Case number '{case_number}' does not conform to divisional format standard (YYYY-XX-XXXXXX).",
                severity=ProceduralDefectSeverity.CURABLE_MINOR,
                page_reference=1,
            ).model_dump()
        )

    # Rule 4: OCR / Extraction Confidence Threshold (FR-ESC-01)
    is_unstructured_pro_se = False
    party_type = state.get("filing_party_type", "")
    if confidence < 0.70 or (party_type == "PRO_SE" and confidence < 0.75):
        is_unstructured_pro_se = True
        defects.append(
            ProceduralDefect(
                rule_citation="Administrative Directive 2026-04(b)",
                defect_description=f"Unstructured Pro Se Pleading / Caption Defect: Extraction confidence ({confidence:.2f} < 0.70) falls below automated rendering threshold. Notice generation suspended pending clerk relief classification.",
                severity=ProceduralDefectSeverity.CURABLE_MINOR,
                page_reference=1,
            ).model_dump()
        )
    elif confidence < 0.88:
        defects.append(
            ProceduralDefect(
                rule_citation="Administrative Directive 2026-04",
                defect_description=f"Low OCR / Extraction Confidence score ({confidence:.2f} < 0.88). Requires manual verification.",
                severity=ProceduralDefectSeverity.CURABLE_MINOR,
                page_reference=1,
            ).model_dump()
        )

    # Severity Evaluation
    if is_emergency:
        severity = "SEV-1"
        requires_clerk = True
    elif is_unstructured_pro_se:
        severity = "SEV-3: UNSTRUCTURED_PRO_SE"
        requires_clerk = True
    elif any(d["severity"] == ProceduralDefectSeverity.MANDATORY_REJECT.value for d in defects):
        severity = "SEV-2"
        requires_clerk = True
    elif any(d["severity"] == ProceduralDefectSeverity.CURABLE_MINOR.value for d in defects):
        severity = "SEV-3"
        requires_clerk = True
    else:
        severity = "CLEAN"
        requires_clerk = False

    workflow_status = "AWAITING_CLERK" if requires_clerk else "VALIDATED"

    return {
        "procedural_defects": defects,
        "severity_level": severity,
        "requires_clerk_review": requires_clerk,
        "workflow_status": workflow_status,
        "pro_se_quarantined": is_unstructured_pro_se,
    }
