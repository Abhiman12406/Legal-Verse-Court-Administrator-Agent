from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DeficiencyItem(BaseModel):
    rule_citation: str = Field(description="Exact court or statutory rule citation, e.g. Local Rule 5.4(a)")
    defect_description: str = Field(description="Factual description of the defect without legal advice")
    mandatory_cure_action: str = Field(description="Concrete procedural action required to cure the defect")
    statutory_deadline_days: int = Field(default=14, description="Statutory timeframe granted to cure")


class DeficiencyCureNoticeSchema(BaseModel):
    case_number: str = Field(description="Canonical case identifier, e.g. 2026-CV-004812")
    court_district: str = Field(default="TRIAL COURT OF THE JUDICIAL DISTRICT", description="Court identifier")
    filing_title: str = Field(description="Title of the defective pleading or motion")
    deficiencies: List[DeficiencyItem] = Field(description="Itemized procedural deficiencies cited")
    statutory_cure_days: int = Field(default=14, description="Standard statutory cure window in calendar days")
    discretionary_instructions: str = Field(
        description="Strictly procedural instructions for re-submission. Must never offer legal advice or substantive commentary."
    )
    clerk_signature_block: str = Field(default="CLERK OF COURT / AUTOMATED DOCKET GATEWAY")


class DiscretionaryHearingNoticeSchema(BaseModel):
    case_number: str
    court_district: str = Field(default="TRIAL COURT OF THE JUDICIAL DISTRICT")
    hearing_type: str = Field(description="Hearing matter title")
    assigned_judge: str
    courtroom: str
    scheduled_date: str
    start_time: str
    ada_accommodations_locked: List[str] = Field(default_factory=list)
    procedural_instructions: List[str] = Field(
        description="Procedural guidelines for calendar call, electronic evidence submission, or virtual appearance."
    )


class InstructorNoticeGenerator:
    """
    Constrained LLM Reasoning Gate:
    Uses Instructor to force strict Pydantic JSON outputs according to pre-vetted court notice schemas.
    Enforces Substantive Non-Interference: strictly procedural, zero legal advice.
    """

    @classmethod
    def generate_deficiency_cure_notice(
        cls,
        case_number: str,
        document_title: str,
        defects: List[Dict[str, Any]],
        court_district: str = "TRIAL COURT OF THE JUDICIAL DISTRICT",
    ) -> DeficiencyCureNoticeSchema:
        api_key = os.getenv("GEMINI_API_KEY", "")

        # Try Instructor with Gemini if key is provided
        if api_key and not api_key.startswith("mock_"):
            try:
                import instructor
                from google import genai

                client = genai.Client(api_key=api_key)
                patched_client = instructor.from_gemini(
                    client=client,
                    mode=instructor.Mode.GEMINI_JSON,
                )

                prompt = (
                    f"Generate a formal procedural deficiency cure notice for court filing.\n"
                    f"Case: {case_number}\n"
                    f"Title: {document_title}\n"
                    f"Defects:\n"
                    + "\n".join(f"- {d.get('rule_citation')}: {d.get('defect_description')}" for d in defects)
                    + "\n\nCONSTITUTIONAL BOUNDARY: You are a court administration agent. "
                    "Provide ONLY procedural compliance instructions. Do NOT provide legal advice or predict outcomes."
                )

                response = patched_client.chat.completions.create(
                    model="gemini-2.5-flash",
                    response_model=DeficiencyCureNoticeSchema,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response
            except Exception:
                pass  # Fallback to deterministic typed schema construction

        # Deterministic schema synthesis conforming to strict schema
        items = [
            DeficiencyItem(
                rule_citation=d.get("rule_citation", "Local Rule 5.4"),
                defect_description=d.get("defect_description", "Procedural defect detected"),
                mandatory_cure_action=(
                    "Submit replacement pleading containing required signature block."
                    if "signature" in d.get("defect_description", "").lower()
                    else "File compliant Certificate of Service certifying notice to all parties of record."
                ),
                statutory_deadline_days=14,
            )
            for d in defects
        ]

        instructions = (
            f"The filing party must cure all stated procedural deficiencies within fourteen (14) calendar days. "
            f"Amended pleadings must be submitted via the electronic filing gateway with the docket fee receipt and certificate of service. "
            f"Failure to timely cure will result in dismissal without prejudice."
        )

        return DeficiencyCureNoticeSchema(
            case_number=case_number,
            court_district=court_district,
            filing_title=document_title,
            deficiencies=items,
            statutory_cure_days=14,
            discretionary_instructions=instructions,
        )

    @classmethod
    def generate_hearing_notice(
        cls,
        case_number: str,
        hearing_type: str,
        assigned_judge: str,
        courtroom: str,
        scheduled_date: str,
        start_time: str,
        accommodations: Optional[List[str]] = None,
    ) -> DiscretionaryHearingNoticeSchema:
        accommodations = accommodations or []
        instructions = [
            "All counsel and self-represented litigants must check in 15 minutes prior to calendar call.",
            "Exhibits must be pre-marked and uploaded to the digital evidence portal no later than 48 hours before the hearing.",
        ]
        if "ASL_INTERPRETER" in accommodations:
            instructions.append("Court-certified ASL interpreter has been assigned and scheduled for this proceeding.")
        if "SPANISH_INTERPRETER" in accommodations:
            instructions.append("Court-certified Spanish interpreter has been assigned and scheduled for this proceeding.")
        if "WHEELCHAIR_ACCESSIBLE" in accommodations:
            instructions.append("Courtroom is ADA compliant with accessible counsel tables.")

        return DiscretionaryHearingNoticeSchema(
            case_number=case_number,
            hearing_type=hearing_type,
            assigned_judge=assigned_judge,
            courtroom=courtroom,
            scheduled_date=scheduled_date,
            start_time=start_time,
            ada_accommodations_locked=accommodations,
            procedural_instructions=instructions,
        )
