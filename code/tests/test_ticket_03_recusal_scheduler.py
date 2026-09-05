import pytest
from fastapi.testclient import TestClient

from lexis_ops.server import app
from lexis_ops.schemas.scheduling import (
    CorporateDisclosureStatement,
    JudicialConflictRecord,
    InterDivisionalTransferNotice,
    ConflictAwareScheduleRequest,
    ConflictAwareScheduleResponse,
)
from lexis_ops.subgraphs.scheduling import (
    solve_conflict_aware_schedule_cpsat,
    InterDivisionalTransferRequired,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_recusal_scheduler_excludes_conflicted_judge():
    """
    Test 28 U.S.C. § 455 Conflict Avoidance:
    When Party discloses corporate parent 'Acme Global Holdings',
    Judge A (who holds stock in Acme Global Holdings) must be mathematically excluded,
    and the solver must assign non-conflicted Judge B.
    """
    disclosure = CorporateDisclosureStatement(
        party_name="Acme Widgets LLC",
        parent_corporations=["Acme Global Holdings Inc."],
        publicly_held_affiliates=["Acme International Ltd."],
    )
    
    conflict_roster = [
        JudicialConflictRecord(
            judge_id="JUDGE-CIVIL-01",
            judge_name="Hon. Sarah Vance",
            disqualified_entities=["Acme Global Holdings Inc.", "MegaCorp"],
            recusal_reason="FINANCIAL_INTEREST_28_USC_455",
        ),
        JudicialConflictRecord(
            judge_id="JUDGE-CIVIL-02",
            judge_name="Hon. Marcus Brody",
            disqualified_entities=["TechGiant Inc."],
            recusal_reason="PRIOR_REPRESENTATION_28_USC_455",
        ),
    ]
    
    result = solve_conflict_aware_schedule_cpsat(
        case_number="2026-CV-088192",
        candidate_judges=["JUDGE-CIVIL-01", "JUDGE-CIVIL-02"],
        corporate_disclosures=[disclosure],
        conflict_roster=conflict_roster,
        statutory_buffer_days=21,
    )
    
    # Must successfully schedule
    assert result.scheduled_slot is not None
    # Must NOT assign conflicted Judge 01
    assert result.scheduled_slot.assigned_judge_id == "JUDGE-CIVIL-02"
    # Recusal report must verify conflict screen
    assert "JUDGE-CIVIL-01" in result.conflicted_judges_excluded
    assert result.status == "SCHEDULED"


def test_division_wide_conflict_triggers_interdivisional_transfer():
    """
    Test Division-Wide Infeasibility Fallback:
    When ALL candidate judges in the division have disqualifying financial interests,
    the solver must raise InterDivisionalTransferRequired and return a formal
    draft Certificate of Recusal to the Chief District Judge.
    """
    disclosure = CorporateDisclosureStatement(
        party_name="PetroEnergy Conglomerate",
        parent_corporations=["Standard Energy Group"],
        financial_interest_entities=["Standard Energy Group"],
    )
    
    # Both judges in division hold financial interests in Standard Energy Group
    conflict_roster = [
        JudicialConflictRecord(
            judge_id="JUDGE-CIVIL-01",
            judge_name="Hon. Sarah Vance",
            disqualified_entities=["Standard Energy Group"],
            recusal_reason="FINANCIAL_INTEREST_28_USC_455",
        ),
        JudicialConflictRecord(
            judge_id="JUDGE-CIVIL-02",
            judge_name="Hon. Marcus Brody",
            disqualified_entities=["Standard Energy Group"],
            recusal_reason="FINANCIAL_INTEREST_28_USC_455",
        ),
    ]
    
    result = solve_conflict_aware_schedule_cpsat(
        case_number="2026-CV-099411",
        candidate_judges=["JUDGE-CIVIL-01", "JUDGE-CIVIL-02"],
        corporate_disclosures=[disclosure],
        conflict_roster=conflict_roster,
        statutory_buffer_days=21,
    )
    
    assert result.scheduled_slot is None
    assert result.status == "MANDATORY_DISQUALIFICATION_TRANSFER"
    assert result.transfer_notice is not None
    assert result.transfer_notice.routed_to == "CHIEF_DISTRICT_JUDGE"
    assert "28 U.S.C. § 455" in result.transfer_notice.certificate_of_recusal_text
    assert len(result.conflicted_judges_excluded) == 2


def test_post_scheduling_solve_api_endpoint(client):
    """
    Test POST /scheduling/solve API endpoint:
    Returns scheduled slot or transfer notice with complete audit payload.
    """
    payload = {
        "case_number": "2026-CV-011223",
        "statutory_buffer_days": 21,
        "accommodations": ["SPANISH_INTERPRETER"],
        "candidate_judges": ["JUDGE-CIVIL-01", "JUDGE-CIVIL-02"],
        "corporate_disclosures": [
            {
                "party_name": "BioPharma Corp",
                "parent_corporations": ["Global Life Sciences"],
                "publicly_held_affiliates": [],
                "financial_interest_entities": ["Global Life Sciences"],
            }
        ],
        "conflict_roster": [
            {
                "judge_id": "JUDGE-CIVIL-01",
                "judge_name=" : "Hon. Sarah Vance",
                "disqualified_entities": ["Global Life Sciences"],
                "recusal_reason": "FINANCIAL_INTEREST_28_USC_455",
            }
        ],
    }
    
    res = client.post("/scheduling/solve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SCHEDULED"
    assert data["scheduled_slot"]["assigned_judge_id"] == "JUDGE-CIVIL-02"
    assert data["scheduled_slot"]["interpreter_locked"] is True
    assert "JUDGE-CIVIL-01" in data["conflicted_judges_excluded"]
