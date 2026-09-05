from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from lexis_ops.db.session import Base


class CaseModel(Base):
    """
    ACID-compliant storage for judicial case records.
    """
    __tablename__ = "cases"

    case_number = Column(String(64), primary_key=True, index=True)
    case_title = Column(String(255), nullable=False)
    court_division = Column(String(128), default="CIVIL DIVISION")
    assigned_judge_id = Column(String(128), nullable=True)
    case_type = Column(String(64), default="CIVIL")
    is_sealed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    filings = relationship("FilingModel", back_populates="case", cascade="all, delete-orphan")


class FilingModel(Base):
    """
    Active docket pleading storage enforcing ACID compliance and statutory metadata fields.
    """
    __tablename__ = "filings"

    id = Column(String(64), primary_key=True, index=True)
    case_number = Column(String(64), ForeignKey("cases.case_number"), nullable=False, index=True)
    case_id = Column(String(128), nullable=True)
    court_division = Column(String(128), default="CIVIL DIVISION")
    assigned_judge_id = Column(String(128), nullable=True)
    document_title = Column(String(255), nullable=False)
    party_type = Column(String(64), default="PLAINTIFF")
    filing_date = Column(String(32), nullable=False)
    is_emergency = Column(Boolean, default=False)
    is_sealed = Column(Boolean, default=False, nullable=False)
    severity_level = Column(String(64), default="CLEAN")
    workflow_status = Column(String(64), default="INGESTED")
    docket_status = Column(String(64), default="CONDITIONALLY_LODGED")
    extraction_confidence = Column(Float, default=1.0)
    signature_detected = Column(Boolean, default=False)
    certificate_of_service_valid = Column(Boolean, default=False)
    raw_text = Column(Text, default="")
    defects = Column(JSON, default=list)
    clerk_decision = Column(JSON, nullable=True)
    scheduled_slot = Column(JSON, nullable=True)
    generated_notice = Column(JSON, nullable=True)
    relief_designation = Column(String(255), nullable=True)
    pro_se_quarantined = Column(Boolean, default=False)
    cure_deadline = Column(String(64), nullable=True)
    lodged_receipt_timestamp = Column(String(64), default="")
    conflict_screen_passed = Column(Boolean, default=False)
    conflicted_judges_excluded = Column(JSON, default=list)
    is_ifp_pending = Column(Boolean, default=False)
    ifp_detected = Column(Boolean, default=False)
    ifp_ruling = Column(JSON, nullable=True)
    is_ex_parte_tro = Column(Boolean, default=False)
    rule_65b_notice_certified = Column(Boolean, nullable=True)
    ex_parte_action = Column(String(128), nullable=True)
    castro_notice = Column(JSON, nullable=True)
    castro_tracking_token = Column(String(128), nullable=True)
    castro_election_status = Column(String(64), nullable=True)
    is_castro_response = Column(Boolean, default=False)
    castro_election = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    case = relationship("CaseModel", back_populates="filings")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id or f"case-{self.case_number.lower()}",
            "case_number": self.case_number,
            "court_division": self.court_division,
            "assigned_judge_id": self.assigned_judge_id or "HON. ELENA CARTER",
            "document_title": self.document_title,
            "party_type": self.party_type,
            "filing_date": self.filing_date,
            "is_emergency": bool(self.is_emergency),
            "is_sealed": bool(self.is_sealed),
            "severity_level": self.severity_level,
            "workflow_status": self.workflow_status,
            "docket_status": self.docket_status,
            "extraction_confidence": float(self.extraction_confidence or 1.0),
            "signature_detected": bool(self.signature_detected),
            "certificate_of_service_valid": bool(self.certificate_of_service_valid),
            "raw_text": self.raw_text,
            "defects": self.defects or [],
            "clerk_decision": self.clerk_decision,
            "scheduled_slot": self.scheduled_slot,
            "generated_notice": self.generated_notice,
            "relief_designation": self.relief_designation,
            "pro_se_quarantined": bool(self.pro_se_quarantined),
            "cure_deadline": self.cure_deadline,
            "lodged_receipt_timestamp": self.lodged_receipt_timestamp or "",
            "conflict_screen_passed": bool(self.conflict_screen_passed),
            "conflicted_judges_excluded": self.conflicted_judges_excluded or [],
            "is_ifp_pending": bool(self.is_ifp_pending),
            "ifp_detected": bool(self.ifp_detected),
            "ifp_ruling": self.ifp_ruling,
            "is_ex_parte_tro": bool(self.is_ex_parte_tro),
            "rule_65b_notice_certified": self.rule_65b_notice_certified,
            "ex_parte_action": self.ex_parte_action,
            "castro_notice": self.castro_notice,
            "castro_tracking_token": self.castro_tracking_token,
            "castro_election_status": self.castro_election_status,
            "is_castro_response": bool(self.is_castro_response),
            "castro_election": self.castro_election,
        }


class AuditLogModel(Base):
    """
    Append-only cryptographically verified audit log.
    Records model version, prompt hash, decision, clerk overrides, and SHA-256 chain.
    """
    __tablename__ = "audit_logs"

    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String(64), nullable=False)
    case_id = Column(String(128), nullable=False, index=True)
    filing_id = Column(String(128), nullable=False, index=True)
    agent_version = Column(String(64), default="2.0.0-ACID")
    model_version = Column(String(64), default="gemini-2.5-flash")
    prompt_hash = Column(String(64), default="")
    event_type = Column(String(128), nullable=False, index=True)
    operator_id = Column(String(128), nullable=False)
    decision = Column(String(128), default="")
    decision_payload = Column(JSON, default=dict)
    clerk_override = Column(JSON, nullable=True)
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "case_id": self.case_id,
            "filing_id": self.filing_id,
            "agent_version": self.agent_version or "2.0.0-ACID",
            "model_version": self.model_version or "gemini-2.5-flash",
            "prompt_hash": self.prompt_hash or "",
            "event_type": self.event_type,
            "operator_id": self.operator_id,
            "decision": self.decision or "",
            "decision_payload": self.decision_payload or {},
            "clerk_override": self.clerk_override,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
        }
