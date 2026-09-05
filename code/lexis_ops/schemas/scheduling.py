from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from lexis_ops.schemas.state import ScheduledSlot


class CorporateDisclosureStatement(BaseModel):
    """
    Statement of Corporate Affiliations under Fed. R. Civ. P. 7.1.
    Required for any nongovernmental corporate party to disclose parent
    corporations, publicly held affiliates, or direct financial interests.
    """
    party_name: str = Field(description="Name of the party filing the disclosure")
    parent_corporations: List[str] = Field(default_factory=list, description="Direct or ultimate parent corporations")
    publicly_held_affiliates: List[str] = Field(default_factory=list, description="Publicly held corporations owning 10%+ stock")
    financial_interest_entities: List[str] = Field(default_factory=list, description="Other entities with financial stake in outcome")

    def all_affiliated_entities(self) -> List[str]:
        """Returns normalized set of all disclosed corporate entities."""
        entities = set()
        if self.party_name:
            entities.add(self.party_name.strip())
        for e in self.parent_corporations + self.publicly_held_affiliates + self.financial_interest_entities:
            if e and e.strip():
                entities.add(e.strip())
        return list(entities)


class JudicialConflictRecord(BaseModel):
    """
    Official judicial financial disclosure & prior representation conflict record.
    Enforces statutory disqualification under 28 U.S.C. § 455 and Canon 3.
    """
    judge_id: str = Field(description="Unique judge identifier, e.g. JUDGE-CIVIL-01")
    judge_name: str = Field(default="", description="Formal name of the judicial officer")
    disqualified_entities: List[str] = Field(description="Entities in which judge holds financial/personal disqualification")
    recusal_reason: str = Field(default="FINANCIAL_INTEREST_28_USC_455", description="Statutory recusal basis")


class InterDivisionalTransferNotice(BaseModel):
    """
    Statutory Certificate of Recusal & Transfer Request to Chief District Judge
    generated when all candidate judges in a division are disqualified by conflict.
    """
    case_number: str
    division: str = "CIVIL DIVISION"
    reason: str = "ALL_DIVISIONAL_JUDGES_DISQUALIFIED_28_USC_455"
    conflicted_judges: List[str] = Field(default_factory=list)
    disqualifying_entities: List[str] = Field(default_factory=list)
    certificate_of_recusal_text: str = ""
    routed_to: str = "CHIEF_DISTRICT_JUDGE"


class ConflictAwareScheduleRequest(BaseModel):
    case_number: str
    statutory_buffer_days: int = 21
    accommodations: List[str] = Field(default_factory=list)
    candidate_judges: List[str] = Field(default_factory=lambda: ["JUDGE-CIVIL-01", "JUDGE-CIVIL-02", "JUDGE-CIVIL-03"])
    candidate_courtrooms: List[str] = Field(default_factory=lambda: ["CR-101", "CR-102", "CR-201"])
    corporate_disclosures: List[CorporateDisclosureStatement] = Field(default_factory=list)
    conflict_roster: List[JudicialConflictRecord] = Field(default_factory=list)


class ConflictAwareScheduleResponse(BaseModel):
    case_number: str
    status: str = Field(description="SCHEDULED or MANDATORY_DISQUALIFICATION_TRANSFER")
    scheduled_slot: Optional[ScheduledSlot] = None
    transfer_notice: Optional[InterDivisionalTransferNotice] = None
    conflicted_judges_excluded: List[str] = Field(default_factory=list)
    conflict_reasons: Dict[str, str] = Field(default_factory=dict)
