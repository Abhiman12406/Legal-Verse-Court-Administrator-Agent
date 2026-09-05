import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from lexis_ops.server import app
from lexis_ops.pdf_rule_validator import PDFRuleValidator, validate_pdf_rules
from lexis_ops.schemas.state import FilingStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_ex_parte_tro_without_rule_65b_certification_triggers_sev1_halt():
    """
    Test Fed. R. Civ. P. 65(b)(1)(B) & Granny Goose Foods v. Teamsters, 415 U.S. 423 (1974):
    An emergency ex parte TRO application lacking attorney certification in writing
    of notice efforts (or why notice should be excused) must trigger SEV-1 halt
    and flag rule_65b_notice_certified = False.
    """
    unnoticed_tro_text = """
    UNITED STATES DISTRICT COURT
    FIRST JUDICIAL DISTRICT
    CASE NO: 2026-CV-887711

    MARY WILSON,
        Plaintiff Pro Se,
    v.
    METROPOLIS HOUSING CORP,
        Defendant.

    EMERGENCY EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER AND STAY OF WRIT

    Plaintiff moves ex parte for immediate emergency injunction halting lockout.
    Lockout scheduled for tomorrow at 8:00 AM.
    
    Date: September 4, 2026
    /s/ Mary Wilson
    """
    result = validate_pdf_rules(unnoticed_tro_text.encode("utf-8"), filename="emergency_tro.pdf")

    assert result.is_emergency is True
    assert result.is_ex_parte_tro is True
    assert result.rule_65b_notice_certified is False
    assert result.severity_level == "SEV-1"
    assert any("65(b)" in d.rule_citation for d in result.procedural_defects)


def test_ex_parte_tro_with_valid_rule_65b_certification_clears_gate():
    """
    When emergency motion contains sworn Rule 65(b)(1)(B) certification detailing
    immediate irreparable injury prior to notice, rule_65b_notice_certified must be True.
    """
    certified_tro_text = """
    UNITED STATES DISTRICT COURT
    FIRST JUDICIAL DISTRICT
    CASE NO: 2026-CV-887711

    MARY WILSON,
        Plaintiff,
    v.
    METROPOLIS HOUSING CORP,
        Defendant.

    EMERGENCY EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER

    CERTIFICATE OF COUNSEL PURSUANT TO FED. R. CIV. P. 65(b)(1)(B):
    I hereby certify in writing that on September 4, 2026 at 09:00 AM, I attempted telephonic
    notice to Defendant's managing agent. Notice could not be completed prior to filing because
    immediate and irreparable injury, loss, or damage will result before the adverse party
    can be heard in opposition, specifically the destruction of tenant property and physical lockout.
    
    Date: September 4, 2026
    /s/ Jonathan Blake, Esq.
    
    CERTIFICATE OF SERVICE
    Served via email to agent@metropolishousing.com on Sept 4, 2026.
    """
    result = validate_pdf_rules(certified_tro_text.encode("utf-8"), filename="certified_tro.pdf")

    assert result.is_emergency is True
    assert result.is_ex_parte_tro is True
    assert result.rule_65b_notice_certified is True


def test_judicial_tri_partite_action_expedited_notice(client):
    """
    Tri-Partite Option 1: ISSUE_EXPEDITED_NOTICE_ORDER
    Judge orders expedited 4-hour telephonic / electronic service with emergency hearing within 24 hours.
    """
    res = client.post(
        "/filings/frcp65b-adjudicate",
        json={
            "case_number": "2026-CV-887711",
            "filing_id": "filing-002",
            "judge_id": "HON. MARCUS VANCE",
            "action": "ISSUE_EXPEDITED_NOTICE_ORDER",
            "judicial_findings": "Notice omitted; expedited 4-hour telephonic service ordered with hearing at 2:00 PM tomorrow.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "EXPEDITED_NOTICE_ORDERED"
    assert data["hearing_window_hours"] == 24
    assert "Expedited Notice Order" in data["notice_order_title"]
    assert data["audit_entry_id"] is not None


def test_judicial_tri_partite_action_override_emergency_grant(client):
    """
    Tri-Partite Option 2: JUDICIAL_OVERRIDE_EMERGENCY_TRO
    Judge enters explicit statutory finding of imminent irreparable harm dispensing with notice under Rule 65(b)(2).
    """
    res = client.post(
        "/filings/frcp65b-adjudicate",
        json={
            "case_number": "2026-CV-887711",
            "filing_id": "filing-002",
            "judge_id": "HON. MARCUS VANCE",
            "action": "JUDICIAL_OVERRIDE_EMERGENCY_TRO",
            "judicial_findings": "Irreparable physical lockout imminent within 12 hours. Notice excused under Rule 65(b)(2).",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "EX_PARTE_TRO_GRANTED"
    assert data["tro_effective_days"] == 14
    assert "Temporary Restraining Order" in data["notice_order_title"]
    assert data["audit_entry_id"] is not None


def test_judicial_tri_partite_action_declassify_standard_motion(client):
    """
    Tri-Partite Option 3: DECLASSIFY_TO_STANDARD_MOTION
    Judge denies ex parte treatment and declassifies application to standard noticed motion with 21-day notice.
    """
    res = client.post(
        "/filings/frcp65b-adjudicate",
        json={
            "case_number": "2026-CV-887711",
            "filing_id": "filing-002",
            "judge_id": "HON. MARCUS VANCE",
            "action": "DECLASSIFY_TO_STANDARD_MOTION",
            "judicial_findings": "No bona fide emergency demonstrated; movant must proceed with standard noticed motion.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "DECLASSIFIED_STANDARD_MOTION"
    assert data["notice_buffer_days"] == 21
    assert data["docket_status"] == FilingStatus.VALIDATED.value
    assert data["audit_entry_id"] is not None
