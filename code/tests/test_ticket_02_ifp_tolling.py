import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from lexis_ops.server import app
from lexis_ops.pdf_rule_validator import PDFRuleValidator, validate_pdf_rules
from lexis_ops.schemas.state import FilingStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_ifp_fee_waiver_detection_at_ingress():
    """
    Test 28 U.S.C. § 1915 IFP Detection:
    When an indigent litigant submits Form AO 240 or an Application to Proceed In Forma Pauperis,
    the Ingress engine must detect the IFP petition, flag is_ifp_pending = True,
    and freeze all automated deficiency clocks.
    """
    ifp_document_text = """
    UNITED STATES DISTRICT COURT
    FIRST JUDICIAL DISTRICT

    CASE NO: 2026-CV-055190
    
    APPLICATION TO PROCEED IN DISTRICT COURT WITHOUT PREPAYING FEES OR COSTS
    (FORM AO 240 - IN FORMA PAUPERIS)

    I, Marcus Vance, declare that I am unable to pay the costs of these proceedings
    or to give security therefor. My monthly income is $0 and I receive public assistance.
    
    I declare under penalty of perjury that the foregoing is true and correct.
    
    Date: September 4, 2026
    /s/ Marcus Vance
    Marcus Vance, Plaintiff Pro Se
    """
    result = validate_pdf_rules(ifp_document_text.encode("utf-8"), filename="ao240_ifp_application.pdf")
    
    assert result.is_ifp_pending is True
    assert result.ifp_detected is True
    # Statutory cure deadline must be suspended (tolled under 28 U.S.C. § 1915)
    assert result.cure_deadline == "FROZEN_PENDING_IFP_RULING" or result.cure_deadline is None
    assert result.docket_status == FilingStatus.CONDITIONALLY_LODGED.value


def test_post_ifp_ruling_grant(client):
    """
    Test Judicial IFP Grant Workflow:
    When court enters an order granting IFP, fees are permanently waived,
    is_ifp_pending is cleared, and status transitions to VALIDATED or SCHEDULED.
    """
    res = client.post(
        "/filings/ifp-ruling",
        json={
            "case_number": "2026-CV-055190",
            "filing_id": "filing-ifp-01",
            "judge_id": "HON. SARAH LIN",
            "decision": "GRANT",
            "ruling_notes": "Financial affidavit verified. Indigency standard satisfied under 28 U.S.C. § 1915.",
            "effective_date": "2026-09-04",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "IFP_GRANTED"
    assert data["fee_waived"] is True
    assert data["is_ifp_pending"] is False
    assert data["audit_entry_id"] is not None


def test_post_ifp_ruling_deny_enforces_21_day_grace_period(client):
    """
    Test Judicial IFP Denial & 21-Day Grace Period:
    Under Williams-Guice v. Board of Education, 45 F.3d 161, denying an IFP petition
    cannot result in immediate dismissal; the litigant must be granted a statutory
    21-day fee tender grace period.
    """
    effective_date = "2026-09-04"
    res = client.post(
        "/filings/ifp-ruling",
        json={
            "case_number": "2026-CV-055190",
            "filing_id": "filing-ifp-01",
            "judge_id": "HON. SARAH LIN",
            "decision": "DENY",
            "ruling_notes": "Applicant monthly income exceeds statutory poverty thresholds.",
            "effective_date": effective_date,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "IFP_DENIED"
    assert data["fee_waived"] is False
    assert data["is_ifp_pending"] is False
    
    # Must compute exact 21-day grace deadline
    expected_grace_deadline = (date.fromisoformat(effective_date) + timedelta(days=21)).isoformat()
    assert data["fee_grace_deadline"] == expected_grace_deadline
    assert "Notice of IFP Denial & Order to Tender Filing Fee" in data["notice_title"]
    assert "21 CALENDAR DAYS" in data["notice_text"]
