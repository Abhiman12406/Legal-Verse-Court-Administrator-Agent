from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class FilingPartyType(str, Enum):
    PLAINTIFF = "PLAINTIFF"
    DEFENDANT = "DEFENDANT"
    INTERVENOR = "INTERVENOR"
    PRO_SE = "PRO_SE"


class FilingStatus(str, Enum):
    """
    Statutory filing status aligning with Fed. R. Civ. P. 5(d)(4).
    Clerks lack authority to unilaterally reject filings; defective filings
    enter CONDITIONALLY_LODGED with a 14-day cure window before potential
    judicial striking.
    """
    CONDITIONALLY_LODGED = "CONDITIONALLY_LODGED"
    VALIDATED = "VALIDATED"
    AWAITING_CLERK = "AWAITING_CLERK"
    DEFICIENT = "DEFICIENT"
    PENDING_JUDICIAL_STRIKE = "PENDING_JUDICIAL_STRIKE"
    STRICKEN_BY_COURT = "STRICKEN_BY_COURT"
    HALTED_SECURITY = "HALTED_SECURITY"


class ProceduralDefectSeverity(str, Enum):
    CURABLE_MINOR = "CURABLE_MINOR"        # e.g., missing phone number in caption
    MANDATORY_REJECT = "MANDATORY_REJECT"  # e.g., zero signature, unserved party
    EMERGENCY_HALT = "EMERGENCY_HALT"      # e.g., stay of execution filed incorrectly / ex parte emergency


class ProposedOrderToStrike(BaseModel):
    """
    Formal judicial council proposed order to strike a pleading,
    prepared automatically when a 14-day statutory cure period expires without cure.
    Striking remains an exclusive Article III / judicial officer function.
    """
    case_number: str
    filing_title: str
    defects_cited: List[str]
    cure_expired_date: str
    order_text: str
    proposed_by: str = "SYSTEM_DOCKET_ENGINE"
    requires_judicial_hmac: bool = True


class CastroElectionOption(str, Enum):
    AFFIRM = "AFFIRM"
    AMEND = "AMEND"
    WITHDRAW = "WITHDRAW"


class CastroRecharacterizationNotice(BaseModel):
    """
    Mandatory Castro v. United States, 540 U.S. 375 (2003) recharacterization notice.
    When a court recharacterizes an unstructured pro se pleading into a formal motion,
    it must warn of preclusive consequences (successive bar, res judicata),
    provide a 14-day statutory election form, and include a machine-readable token.
    """
    case_number: str
    filing_id: str
    original_filing_title: str
    received_date: str
    proposed_recharacterization: str
    castro_tracking_token: str
    election_deadline: str
    notice_text: str
    election_options: List[str] = Field(default_factory=lambda: ["AFFIRM", "AMEND", "WITHDRAW"])
    status: str = "PENDING_ELECTION"



class CaptionLayoutDescriptor(BaseModel):
    """
    Encapsulates pleading caption layout analysis, pro se identification,
    and structural confidence scoring, resolving primitive obsession.
    """
    case_number: Optional[str] = Field(default=None, description="Extracted standard case number YYYY-XX-XXXXXX")
    document_title: str = Field(default="GENERAL PLEADING", description="Extracted or synthesized filing title")
    party_type: FilingPartyType = Field(default=FilingPartyType.PLAINTIFF)
    has_formal_caption: bool = Field(default=False)
    is_pro_se: bool = Field(default=False)
    is_informal_or_handwritten: bool = Field(default=False)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    def compute_confidence(self) -> float:
        """
        Computes calibrated extraction confidence based on structural caption fidelity.
        - Formal caption with case number: 0.98 - 0.99
        - Partial caption / missing case number: 0.68 - 0.85
        - Unstructured pro se / informal / handwritten: 0.64 (triggers SEV-3 quarantine < 0.70)
        """
        if self.is_informal_or_handwritten or (self.is_pro_se and not self.has_formal_caption):
            return 0.64
        if not self.has_formal_caption or not self.case_number:
            return 0.68
        return 0.98

    @classmethod
    def from_raw_text(cls, raw_text: str, filename: str = "filing.pdf") -> CaptionLayoutDescriptor:
        import re

        text_upper = raw_text.upper()
        case_match = re.search(r"\b(\d{4}-[A-Z]{2}-\d{5,6})\b", raw_text)
        case_number = case_match.group(1) if case_match else None

        # Party type resolution
        if "PRO SE" in text_upper or "IN PROPER PERSON" in text_upper or "DEFENDANT PRO SE" in text_upper:
            party = FilingPartyType.PRO_SE
            is_pro_se = True
        elif "DEFENDANT" in text_upper and "PLAINTIFF" not in text_upper:
            party = FilingPartyType.DEFENDANT
            is_pro_se = False
        else:
            party = FilingPartyType.PLAINTIFF
            is_pro_se = False

        # Document title detection
        first_lines = [l.strip() for l in raw_text.splitlines() if l.strip()][:10]
        detected_title = filename.replace(".pdf", "").replace("_", " ").title()
        for line in first_lines:
            if any(term in line.lower() for term in ["motion", "petition", "complaint", "notice", "brief", "order", "answer", "application"]):
                detected_title = line
                break

        # Check informal / handwritten / unstructured markers
        informal_markers = [
            "handwritten",
            "informal",
            "unstructured",
            "unclassified",
            "to the clerk",
            "dear judge",
            "writing because",
            "cannot afford",
            "cannot pay",
        ]
        is_informal = any(m in raw_text.lower() for m in informal_markers)
        has_formal_caption = bool(case_number and any(hdr in text_upper for hdr in ["IN THE", "COURT", "DIVISION", "CASE NO"]))

        desc = cls(
            case_number=case_number,
            document_title=detected_title,
            party_type=party,
            has_formal_caption=has_formal_caption,
            is_pro_se=is_pro_se,
            is_informal_or_handwritten=is_informal,
        )
        desc.confidence_score = desc.compute_confidence()
        return desc



class ProceduralDefect(BaseModel):
    rule_citation: str = Field(description="Exact rule code violated, e.g. Local Rule 5.2(b)")
    defect_description: str = Field(description="Clear, neutral, objective statement of defect")
    severity: ProceduralDefectSeverity
    page_reference: Optional[int] = Field(default=None, description="Document page number where defect occurred")


class FilingValidationPayload(BaseModel):
    case_number: str = Field(description="Case number, e.g. 2026-CV-012345")
    document_title: str = Field(description="Title of the motion or pleading")
    party_type: FilingPartyType = Field(default=FilingPartyType.PLAINTIFF)
    filing_date: str = Field(description="Filing date ISO format YYYY-MM-DD")
    signature_detected: bool = Field(default=False)
    certificate_of_service_valid: bool = Field(default=False)
    is_emergency: bool = Field(default=False)
    defects: List[ProceduralDefect] = Field(default_factory=list)
    requires_clerk_escalation: bool = Field(default=False)
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ClerkActionType(str, Enum):
    APPROVE_OVERRIDE = "APPROVE_OVERRIDE"
    ISSUE_DEFICIENCY = "ISSUE_DEFICIENCY"
    REASSIGN_JUDGE = "REASSIGN_JUDGE"


class ClerkDecision(BaseModel):
    action: ClerkActionType
    clerk_id: str
    decision_notes: str
    override_timestamp: Optional[str] = None
    relief_designation: Optional[str] = None
    clerk_token: Optional[str] = None


class ClerkExceptionCard(BaseModel):
    case_number: str
    document_title: str
    severity_level: str
    defects: List[ProceduralDefect]
    confidence: float
    is_emergency: bool
    summary_message: str


class HearingRequest(BaseModel):
    hearing_type: str = Field(default="MOTION_HEARING", description="e.g. MOTION_HEARING, DISCOVERY_CONFERENCE, SUMMARY_JUDGMENT")
    estimated_duration_minutes: int = Field(default=60)
    statutory_buffer_days: int = Field(default=21, description="Minimum days notice required by statute")
    accommodations_required: List[str] = Field(default_factory=list, description="e.g. ASL_INTERPRETER, SPANISH_INTERPRETER")


class ScheduledSlot(BaseModel):
    hearing_id: str
    case_number: str
    courtroom_id: str
    assigned_judge_id: str
    scheduled_date: str
    start_time: str
    duration_minutes: int
    interpreter_locked: bool
    status: str = "CONFIRMED"


class AuditRecord(BaseModel):
    entry_id: int
    timestamp: str
    case_id: str
    filing_id: str
    agent_version: str
    event_type: str
    operator_id: str
    decision_payload: Dict[str, Any]
    previous_hash: str
    current_hash: str
    model_version: Optional[str] = "gemini-2.5-flash"
    prompt_hash: Optional[str] = None
    decision: Optional[str] = None
    clerk_override: Optional[Dict[str, Any]] = None


class LexisOpsState(TypedDict, total=False):
    # Case & Ingestion Context
    case_id: str
    case_number: str
    court_division: str
    assigned_judge_id: str
    case_type: str
    is_sealed: bool
    document_raw_text: str
    document_uri: str
    doc_hash_sha256: str
    
    # Pre-LLM Security Gate
    security_cleared: bool
    security_violations: List[str]
    
    # Extracted Metadata
    filing_party_type: str
    document_title: str
    filing_date: str
    signature_detected: bool
    certificate_of_service_valid: bool
    is_emergency: bool
    extraction_confidence: float
    
    # Procedural Rule Engine Defects
    procedural_defects: List[Dict[str, Any]]
    severity_level: str
    requires_clerk_review: bool
    
    # HITL Clerk Review
    clerk_exception_card: Optional[Dict[str, Any]]
    clerk_decision: Optional[Dict[str, Any]]
    relief_designation: Optional[str]
    pro_se_quarantined: bool
    
    # Scheduling Request & Allocation
    hearing_request: Optional[Dict[str, Any]]
    scheduled_slot: Optional[Dict[str, Any]]
    scheduling_conflict: Optional[str]
    
    # 28 U.S.C. § 1915 In Forma Pauperis Tolling
    is_ifp_pending: bool
    ifp_detected: bool

    # Fed. R. Civ. P. 65(b)(1)(B) Ex Parte Notice Gate
    is_ex_parte_tro: bool
    rule_65b_notice_certified: Optional[bool]
    ex_parte_action: Optional[str]

    # Castro v. United States Pro Se Recharacterization
    castro_notice: Optional[Dict[str, Any]]
    castro_tracking_token: Optional[str]
    castro_election_status: Optional[str]
    castro_token_detected: Optional[str]
    castro_election: Optional[str]
    is_castro_response: Optional[bool]

    # Notice & Audit Ledger
    generated_notices: List[Dict[str, Any]]

    audit_trail: List[Dict[str, Any]]
    latest_audit_hash: str
    workflow_status: str  # INGESTED, HALTED_SECURITY, VALIDATED, AWAITING_CLERK, DEFICIENT, SCHEDULED, ISSUED, COMPLETED

