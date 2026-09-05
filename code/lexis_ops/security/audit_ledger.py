import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from lexis_ops.schemas.state import AuditRecord


class CryptographicAuditLedger:
    """
    Append-only cryptographically chained audit ledger meeting CJIS & FedRAMP standards (PRD Section 6.1 & 7.2).
    Every state change or clerk decision produces a SHA-256 hash linked to the previous entry,
    verifiably binding model version, prompt hash, decision, and clerk overrides.
    """

    GENESIS_HASH = "0" * 64
    AGENT_VERSION = "2.0.0-ACID"
    DEFAULT_MODEL_VERSION = "gemini-2.5-flash"

    @classmethod
    def compute_entry_hash(
        cls,
        previous_hash: str,
        timestamp: str,
        case_id: str,
        filing_id: str,
        event_type: str,
        operator_id: str,
        decision_payload: Dict[str, Any],
        model_version: str = DEFAULT_MODEL_VERSION,
        prompt_hash: Optional[str] = None,
        decision: Optional[str] = None,
        clerk_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        # Deterministic JSON serialization
        payload_serialized = json.dumps(decision_payload or {}, sort_keys=True)
        override_serialized = json.dumps(clerk_override or {}, sort_keys=True) if clerk_override else ""
        raw_string = (
            f"{previous_hash}|{timestamp}|{case_id}|{filing_id}|{event_type}|{operator_id}|"
            f"{model_version}|{prompt_hash or ''}|{decision or ''}|{override_serialized}|{payload_serialized}"
        )
        return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

    @classmethod
    def record_event(
        cls,
        case_id: str,
        filing_id: str,
        event_type: str,
        operator_id: str,
        decision_payload: Dict[str, Any],
        previous_hash: Optional[str] = None,
        entry_id: int = 1,
        model_version: str = DEFAULT_MODEL_VERSION,
        prompt_hash: Optional[str] = None,
        decision: Optional[str] = None,
        clerk_override: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        prev_hash = previous_hash or cls.GENESIS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()
        current_hash = cls.compute_entry_hash(
            previous_hash=prev_hash,
            timestamp=timestamp,
            case_id=case_id,
            filing_id=filing_id,
            event_type=event_type,
            operator_id=operator_id,
            decision_payload=decision_payload,
            model_version=model_version,
            prompt_hash=prompt_hash,
            decision=decision,
            clerk_override=clerk_override,
        )

        return AuditRecord(
            entry_id=entry_id,
            timestamp=timestamp,
            case_id=case_id,
            filing_id=filing_id,
            agent_version=cls.AGENT_VERSION,
            event_type=event_type,
            operator_id=operator_id,
            decision_payload=decision_payload,
            previous_hash=prev_hash,
            current_hash=current_hash,
            model_version=model_version,
            prompt_hash=prompt_hash,
            decision=decision,
            clerk_override=clerk_override,
        )

    @classmethod
    def record_db_event(
        cls,
        db: Session,
        case_id: str,
        filing_id: str,
        event_type: str,
        operator_id: str,
        decision_payload: Dict[str, Any],
        model_version: str = DEFAULT_MODEL_VERSION,
        prompt_hash: Optional[str] = None,
        decision: Optional[str] = None,
        clerk_override: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Appends an entry directly to the database AuditLogModel, chaining cryptographically
        to the latest record in the database.
        """
        from lexis_ops.db.models import AuditLogModel

        last_entry = db.query(AuditLogModel).order_by(AuditLogModel.entry_id.desc()).first()
        prev_hash = last_entry.current_hash if last_entry else cls.GENESIS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()

        current_hash = cls.compute_entry_hash(
            previous_hash=prev_hash,
            timestamp=timestamp,
            case_id=case_id,
            filing_id=filing_id,
            event_type=event_type,
            operator_id=operator_id,
            decision_payload=decision_payload,
            model_version=model_version,
            prompt_hash=prompt_hash,
            decision=decision,
            clerk_override=clerk_override,
        )

        log_obj = AuditLogModel(
            timestamp=timestamp,
            case_id=case_id,
            filing_id=filing_id,
            model_version=model_version,
            prompt_hash=prompt_hash,
            decision=decision,
            clerk_override=clerk_override,
            agent_version=cls.AGENT_VERSION,
            event_type=event_type,
            operator_id=operator_id,
            decision_payload=decision_payload,
            previous_hash=prev_hash,
            current_hash=current_hash,
        )
        db.add(log_obj)
        db.commit()
        db.refresh(log_obj)
        return log_obj

    @classmethod
    def verify_chain(cls, records: List[AuditRecord]) -> bool:
        if not records:
            return True

        for i, record in enumerate(records):
            expected_prev = cls.GENESIS_HASH if i == 0 else records[i - 1].current_hash
            if record.previous_hash != expected_prev:
                return False

            recalculated = cls.compute_entry_hash(
                previous_hash=record.previous_hash,
                timestamp=record.timestamp,
                case_id=record.case_id,
                filing_id=record.filing_id,
                event_type=record.event_type,
                operator_id=record.operator_id,
                decision_payload=record.decision_payload,
                model_version=getattr(record, "model_version", cls.DEFAULT_MODEL_VERSION) or cls.DEFAULT_MODEL_VERSION,
                prompt_hash=getattr(record, "prompt_hash", None),
                decision=getattr(record, "decision", None),
                clerk_override=getattr(record, "clerk_override", None),
            )
            if recalculated != record.current_hash:
                return False

        return True

    @classmethod
    def verify_chain_db(cls, db: Session) -> Dict[str, Any]:
        """
        Verifies the full integrity of the audit logs in the database.
        """
        from lexis_ops.db.models import AuditLogModel

        logs = db.query(AuditLogModel).order_by(AuditLogModel.entry_id.asc()).all()
        if not logs:
            return {"verified": True, "total_records": 0, "message": "Ledger is empty"}

        for i, log in enumerate(logs):
            expected_prev = cls.GENESIS_HASH if i == 0 else logs[i - 1].current_hash
            if log.previous_hash != expected_prev:
                return {
                    "verified": False,
                    "tampered_entry_id": log.entry_id,
                    "error": f"Broken chain link at entry {log.entry_id}. Expected {expected_prev}, got {log.previous_hash}",
                }

            recalculated = cls.compute_entry_hash(
                previous_hash=log.previous_hash,
                timestamp=log.timestamp,
                case_id=log.case_id,
                filing_id=log.filing_id,
                event_type=log.event_type,
                operator_id=log.operator_id,
                decision_payload=log.decision_payload,
                model_version=log.model_version or cls.DEFAULT_MODEL_VERSION,
                prompt_hash=log.prompt_hash,
                decision=log.decision,
                clerk_override=log.clerk_override,
            )
            if recalculated != log.current_hash:
                return {
                    "verified": False,
                    "tampered_entry_id": log.entry_id,
                    "error": f"Cryptographic signature mismatch at entry {log.entry_id}. Stored {log.current_hash}, computed {recalculated}",
                }

        return {
            "verified": True,
            "total_records": len(logs),
            "head_hash": logs[-1].current_hash,
            "message": f"All {len(logs)} audit entries verified against SHA-256 chain root.",
        }
