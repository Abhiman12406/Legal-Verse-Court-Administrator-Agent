import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from lexis_ops.server import app
from lexis_ops.pdf_rule_validator import PDFRuleValidator, validate_pdf_rules
from lexis_ops.subgraphs.deficiency import generate_castro_recharacterization_notice
from lexis_ops.schemas.state import CastroRecharacterizationNotice


@pytest.fixture
def client():
    return TestClient(app)


def test_castro_warning_compilation_contains_mandatory_disclosures():
    """
    Test Castro v. United States, 540 U.S. 375 (2003):
    When an informal pro se paper is recharacterized as a formal motion,
    the court must issue a formal warning disclosing preclusive consequences,
    provide a 14-day election period, and embed a machine-readable tracking token.
    """
    notice = generate_castro_recharacterization_notice(
        case_number="2026-CV-009988",
        filing_id="filing-003",
        original_filing_title="Letter to Judge Regarding Lockout",
        received_date="2026-09-04",
        proposed_recharacterization="Emergency Motion for Stay of Eviction / Writ",
    )

    assert isinstance(notice, CastroRecharacterizationNotice)
    assert notice.case_number == "2026-CV-009988"
    assert notice.filing_id == "filing-003"
    assert notice.castro_tracking_token == "CASTRO-RECLASS-2026-CV-009988-filing-003"
    assert "Castro v. United States" in notice.notice_text
    assert "540 U.S. 375" in notice.notice_text
    # Must warn of legal preclusion (second or successive / res judicata)
    assert "preclusion" in notice.notice_text.lower() or "second or successive" in notice.notice_text.lower()
    # Must provide 14-day election options
    assert "AFFIRM" in notice.election_options
    assert "AMEND" in notice.election_options
    assert "WITHDRAW" in notice.election_options
    # Must have 14-day deadline
    expected_deadline = (date.fromisoformat("2026-09-04") + timedelta(days=14)).isoformat()
    assert notice.election_deadline == expected_deadline


def test_ingress_scanner_detects_castro_reclass_token_and_affirm_election():
    """
    Verify ingress scanner parses CASTRO-RECLASS-<case_id>-<filing_id> token
    and identifies an AFFIRM election response.
    """
    return_form_text = """
    IN THE DISTRICT COURT OF THE FIRST JUDICIAL DISTRICT
    TRACKING TOKEN: CASTRO-RECLASS-2026-CV-009988-filing-003
    CASE NO: 2026-CV-009988

    PRO SE LITIGANT ELECTION RESPONSE FORM
    Pursuant to Castro v. United States, 540 U.S. 375 (2003)

    [X] AFFIRM & PROCEED: I consent to the Court recharacterizing my submission
    as an Emergency Motion for Stay of Eviction / Writ and request adjudication.

    [ ] AMEND
    [ ] WITHDRAW

    Date: September 8, 2026
    /s/ Maria Gonzalez
    """
    result = validate_pdf_rules(return_form_text.encode("utf-8"), filename="castro_response.pdf")

    assert result.is_castro_response is True
    assert result.castro_token_detected == "CASTRO-RECLASS-2026-CV-009988-filing-003"
    assert result.castro_parent_case_id == "2026-CV-009988"
    assert result.castro_parent_filing_id == "filing-003"
    assert result.castro_election == "AFFIRM"


def test_ingress_scanner_detects_castro_withdraw_election():
    """
    Verify ingress scanner detects a WITHDRAW election, avoiding preclusion.
    """
    withdraw_form_text = """
    TRACKING TOKEN: CASTRO-RECLASS-2026-CV-009988-filing-003
    CASE NO: 2026-CV-009988

    [ ] AFFIRM
    [ ] AMEND
    [X] WITHDRAW WITHOUT PREJUDICE: I elect to withdraw this submission to avoid preclusive bar.

    Date: September 8, 2026
    /s/ Maria Gonzalez
    """
    result = validate_pdf_rules(withdraw_form_text.encode("utf-8"), filename="castro_withdraw.pdf")

    assert result.is_castro_response is True
    assert result.castro_token_detected == "CASTRO-RECLASS-2026-CV-009988-filing-003"
    assert result.castro_election == "WITHDRAW"


def test_server_recharacterize_endpoint_generates_notice_and_audit(client):
    """
    Test POST /filings/recharacterize compiles Castro warning and appends
    to SHA-256 cryptographic audit ledger.
    """
    payload = {
        "case_number": "2026-CV-009988",
        "filing_id": "filing-003",
        "original_filing_title": "Informal Pro Se Letter",
        "received_date": "2026-09-04",
        "proposed_recharacterization": "Emergency Motion to Stay Eviction",
        "operator_id": "CLERK_ADMIN_01",
    }
    response = client.post("/filings/recharacterize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "CASTRO_WARNING_ISSUED"
    assert data["tracking_token"] == "CASTRO-RECLASS-2026-CV-009988-filing-003"
    assert "Castro v. United States" in data["notice"]["notice_text"]
    assert "audit_hash" in data


def test_server_castro_election_adjudication_lifecycle(client):
    """
    Test POST /filings/castro-election handles AFFIRM and WITHDRAW elections
    with appropriate docket status updates and audit trails.
    """
    # 1. Litigant affirms
    affirm_payload = {
        "case_number": "2026-CV-009988",
        "filing_id": "filing-003",
        "tracking_token": "CASTRO-RECLASS-2026-CV-009988-filing-003",
        "election": "AFFIRM",
        "operator_id": "SYSTEM_INGRESS",
    }
    affirm_res = client.post("/filings/castro-election", json=affirm_payload)
    assert affirm_res.status_code == 200
    affirm_data = affirm_res.json()
    assert affirm_data["status"] == "ELECTION_PROCESSED"
    assert affirm_data["election"] == "AFFIRM"
    assert affirm_data["docket_status"] == "RECHARACTERIZATION_AFFIRMED"
    assert "audit_hash" in affirm_data

    # 2. Litigant withdraws
    withdraw_payload = {
        "case_number": "2026-CV-009988",
        "filing_id": "filing-003",
        "tracking_token": "CASTRO-RECLASS-2026-CV-009988-filing-003",
        "election": "WITHDRAW",
        "operator_id": "SYSTEM_INGRESS",
    }
    withdraw_res = client.post("/filings/castro-election", json=withdraw_payload)
    assert withdraw_res.status_code == 200
    withdraw_data = withdraw_res.json()
    assert withdraw_data["status"] == "ELECTION_PROCESSED"
    assert withdraw_data["election"] == "WITHDRAW"
    assert withdraw_data["docket_status"] == "WITHDRAWN_BY_MOVANT"
    assert "audit_hash" in withdraw_data
