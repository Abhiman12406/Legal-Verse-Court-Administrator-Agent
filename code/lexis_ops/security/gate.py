import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SecurityGateResult:
    cleared: bool
    is_sealed_breach: bool
    pii_violations: List[str]
    severity: str  # CLEAN or SEV-1


class PreLLMSecurityGate:
    """
    Deterministic pre-LLM security filter ensuring CJIS/FedRAMP compliance
    and enforcing hermetic sealed-record isolation (PRD Section 3.1 & 7.2).
    """

    # SSN / ITIN Pattern: 000-00-0000 (including 9xx ITINs)
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    # Credit Card / Financial Account pattern (16 digits separated by dashes/spaces)
    FINANCIAL_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    # Juvenile name / unredacted minor markers
    JUVENILE_PATTERNS = [
        re.compile(r"\bminor child\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", re.IGNORECASE),
        re.compile(r"\bjuvenile delinquent\s+([A-Z][a-z]+)\b", re.IGNORECASE),
        re.compile(r"\bDOB:\s*\d{2}/\d{2}/(20(?:1[0-9]|2[0-9]))\b", re.IGNORECASE), # Minors born after 2010
    ]

    @classmethod
    def evaluate(cls, is_sealed: bool, raw_text: str, case_type: str = "") -> SecurityGateResult:
        violations: List[str] = []

        # 1. Hermetic Sealed-Record Isolation Check
        is_sealed_breach = False
        if is_sealed or case_type.upper() in ["JUVENILE", "ADOPTION", "MENTAL_HEALTH", "SEALED"]:
            violations.append(
                "SEALED_RECORD_DETECTED: Case is sealed or restricted category. Text prohibited from general LLM ingress."
            )
            is_sealed_breach = True

        # 2. SSN Detection
        ssn_matches = cls.SSN_PATTERN.findall(raw_text)
        if ssn_matches:
            violations.append(f"UNREDACTED_SSN_DETECTED: Found {len(ssn_matches)} unredacted Social Security Number(s).")

        # 3. Financial Account Detection
        financial_matches = cls.FINANCIAL_PATTERN.findall(raw_text)
        if financial_matches:
            violations.append(f"UNREDACTED_FINANCIAL_INFO: Found {len(financial_matches)} payment card/account number(s).")

        # 4. Juvenile PII Detection
        for pat in cls.JUVENILE_PATTERNS:
            matches = pat.findall(raw_text)
            if matches:
                violations.append(f"UNREDACTED_JUVENILE_PII: Found potential unredacted minor identifier: {matches[0]}")
                break

        cleared = len(violations) == 0
        severity = "CLEAN" if cleared else "SEV-1"

        return SecurityGateResult(
            cleared=cleared,
            is_sealed_breach=is_sealed_breach,
            pii_violations=violations,
            severity=severity,
        )
