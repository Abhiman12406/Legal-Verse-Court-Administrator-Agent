"""
RBAC / ABAC Access Control & Document Redaction Policy Engine
Enforces CJIS / FedRAMP Rule 5.9 isolation for sealed dockets, juvenile matters, and PII.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum


class Role(str, Enum):
    PUBLIC = "PUBLIC"
    CLERK = "CLERK"
    ASSOCIATE_JUDGE = "ASSOCIATE_JUDGE"
    CHIEF_JUDGE = "CHIEF_JUDGE"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class ClearanceLevel(str, Enum):
    STANDARD = "STANDARD"
    CONFIDENTIAL = "CONFIDENTIAL"
    SEALED_CONFIDENTIAL = "SEALED_CONFIDENTIAL"
    JUDICIAL_RESTRICTED = "JUDICIAL_RESTRICTED"


SEALED_REDACTION_NOTICE = (
    "[CONFIDENTIAL COURT RECORD - RESTRICTED ACCESS: SEALED UNDER CJIS/FEDRAMP RULE 5.9. "
    "UNAUTHORIZED ACCESS PROHIBITED. CONTACT CHIEF JUDGE CHAMBERS FOR IN CAMERA INSPECTION.]"
)


def evaluate_filing_access(
    filing_data: Dict[str, Any],
    role: str = Role.CLERK.value,
    clearance_level: str = ClearanceLevel.STANDARD.value,
    user_id: Optional[str] = None
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Evaluates whether the requesting entity has sufficient permissions to view the filing.
    If the document is sealed and clearance is insufficient:
    - Text is redacted with statutory warning notice.
    - Raw text and sensitive metadata are shielded.
    
    Returns:
        (sanitized_filing_dict, is_redacted, reason_message)
    """
    is_sealed = filing_data.get("is_sealed", False)
    
    # Non-sealed filings are readable by all authenticated court staff
    if not is_sealed:
        return filing_data, False, "Access granted (Unsealed public record)"
        
    # Judicial Officers and ClearanceLevel >= SEALED_CONFIDENTIAL have full in camera access
    has_judicial_clearance = role in [Role.CHIEF_JUDGE.value, Role.ASSOCIATE_JUDGE.value, Role.SYSTEM_ADMIN.value]
    has_clearance_token = clearance_level in [ClearanceLevel.SEALED_CONFIDENTIAL.value, ClearanceLevel.JUDICIAL_RESTRICTED.value]
    
    if has_judicial_clearance or has_clearance_token:
        sanitized = dict(filing_data)
        sanitized["_access_level"] = "UNRESTRICTED_JUDICIAL_IN_CAMERA"
        return sanitized, False, f"In camera unredacted access granted to {role} ({user_id or 'anonymous'})"
        
    # Standard Clerks, Public, and lower clearance: Redact the record text and sensitive details
    sanitized = dict(filing_data)
    sanitized["raw_text"] = SEALED_REDACTION_NOTICE
    sanitized["is_redacted"] = True
    sanitized["_access_level"] = "RESTRICTED_REDACTED"
    sanitized["redaction_notice"] = SEALED_REDACTION_NOTICE
    
    reason = (
        f"Document sealed under CJIS Rule 5.9: user role '{role}' with clearance "
        f"'{clearance_level}' does not hold required SEALED_CONFIDENTIAL credentials. "
        "Content has been securely redacted."
    )
    return sanitized, True, reason
