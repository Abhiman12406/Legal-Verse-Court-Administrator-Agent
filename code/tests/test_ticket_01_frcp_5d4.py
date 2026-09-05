import hashlib
import hmac
import time
import pytest
from fastapi.testclient import TestClient

from lexis_ops.server import app
from lexis_ops.pdf_rule_validator import PDFRuleValidator, validate_pdf_rules
from lexis_ops.schemas.state import FilingStatus, ProceduralDefectSeverity
from lexis_ops.subgraphs.deficiency import generate_proposed_order_to_strike


@pytest.fixture
def client():
    return TestClient(app)


def test_frcp_5d4_non_refusal_conditional_docketing():
    """
    Test Rule 5(d)(4) Non-Refusal Rule:
    Pleadings with procedural defects (e.g. missing signature or missing certificate of service)
    must receive CONDITIONALLY_LODGED docket status and a microsecond receipt timestamp,
    NEVER an administrative rejection.
    """
    deficient_text = """
    IN THE DISTRICT COURT OF THE FIRST JUDICIAL DISTRICT
    CASE NO: 2026-CV-044210
    
    DEFENDANT'S MOTION FOR EXTENSION OF TIME
    
    Comes now the Defendant and moves for a 30-day extension of time.
    (Document concludes abruptly with no signature block and no proof of service)
    """
    result = validate_pdf_rules(deficient_text.encode("utf-8"), filename="unsigned_motion.pdf")
    
    # Must NOT be marked as valid
    assert result.is_valid is False
    # Under FRCP 5(d)(4), docket status must be CONDITIONALLY_LODGED
    assert result.docket_status == FilingStatus.CONDITIONALLY_LODGED.value
    # Must have microsecond-accurate receipt timestamp
    assert result.lodged_receipt_timestamp is not None
    assert "T" in result.lodged_receipt_timestamp
    # Must compute a 14-day statutory cure deadline
    assert result.cure_deadline is not None
    assert len(result.procedural_defects) >= 1


def test_proposed_order_to_strike_compilation():
    """
    Test automated compilation of [Proposed] Order to Strike Non-Conforming Pleading
    when a conditionally lodged filing's 14-day cure period expires without cure.
    """
    order = generate_proposed_order_to_strike(
        case_number="2026-CV-044210",
        filing_title="DEFENDANT'S MOTION FOR EXTENSION OF TIME",
        defects_cited=["Local Civil Rule 11.1 (Omission of Signature)", "Local Rule 5.2(b) (Missing Certificate of Service)"],
        cure_expired_date="2026-09-18",
    )
    
    assert order.case_number == "2026-CV-044210"
    assert "ORDER TO STRIKE NON-CONFORMING PLEADING" in order.order_text
    assert "Fed. R. Civ. P. 5(d)(4)" in order.order_text or "Rule 11.1" in order.order_text
    assert "Local Civil Rule 11.1" in order.order_text
    assert order.requires_judicial_hmac is True


def test_post_filings_strike_hmac_authorization(client):
    """
    Test POST /filings/strike endpoint:
    Striking a pleading is an Article III judicial act; requires verified judicial HMAC token.
    Unauthenticated or forged requests must be rejected with 403.
    """
    secret = "lexisops-production-secret-clerk-sig-key-2026"
    judge_id = "JUDGE-CIVIL-01"
    case_id = "2026-CV-044210"
    action = "STRIKE_PLEADINGS"
    timestamp = str(int(time.time()))
    
    # Valid HMAC signature: judge_id:case_id:action:timestamp
    payload_to_sign = f"{judge_id}:{case_id}:{action}:{timestamp}"
    signature = hmac.new(secret.encode("utf-8"), payload_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    valid_token = f"{judge_id}:{case_id}:{action}:{timestamp}:{signature}"
    
    # 1. Forged token should fail with 403
    forged_token = f"{judge_id}:{case_id}:{action}:{timestamp}:invalid_signature_hex"
    res_fail = client.post(
        "/filings/strike",
        json={
            "case_number": case_id,
            "filing_id": "filing-test-01",
            "judge_id": judge_id,
            "judicial_token": forged_token,
            "defects_cited": ["Rule 11.1 unsigned"],
        },
    )
    assert res_fail.status_code == 403
    assert "Invalid or forged judicial authorization token" in res_fail.json()["detail"]
    
    # 2. Valid token succeeds and returns STRICKEN_BY_COURT
    res_ok = client.post(
        "/filings/strike",
        json={
            "case_number": case_id,
            "filing_id": "filing-test-01",
            "judge_id": judge_id,
            "judicial_token": valid_token,
            "defects_cited": ["Rule 11.1 unsigned"],
        },
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "STRICKEN_BY_COURT"
    assert data["case_number"] == case_id
    assert data["audit_entry_id"] is not None
