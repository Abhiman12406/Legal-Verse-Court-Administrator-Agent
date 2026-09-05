import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lexis_ops.db.models import CaseModel, FilingModel, AuditLogModel
from lexis_ops.db.rbac import Role, ClearanceLevel, SEALED_REDACTION_NOTICE, evaluate_filing_access
from lexis_ops.db.seed import seed_db
from lexis_ops.db.session import Base, get_db
from lexis_ops.security.audit_ledger import CryptographicAuditLedger
from lexis_ops.server import app


# Test database setup (in-memory SQLite for test isolation)
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_db(db, force=True)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_acid_storage_and_seeding(test_db):
    """Verifies ACID case records, filings, and genesis cryptographic audit chain."""
    cases = test_db.query(CaseModel).all()
    assert len(cases) == 5

    filings = test_db.query(FilingModel).all()
    assert len(filings) == 6

    # Verify genesis audit log entry exists
    audit_logs = test_db.query(AuditLogModel).all()
    assert len(audit_logs) >= 1
    genesis = audit_logs[0]
    assert genesis.model_version == "gemini-2.5-flash"
    assert genesis.prompt_hash is not None
    assert genesis.current_hash is not None
    assert genesis.previous_hash == "0" * 64


def test_rbac_abac_sealed_document_isolation(test_db):
    """
    Verifies that sealed filing (filing-003, juvenile matter) is redacted for standard Clerks/Public
    and unredacted only for Chief Judge / Judicial Restricted clearance.
    """
    sealed_filing = test_db.query(FilingModel).filter(FilingModel.id == "filing-003").first()
    assert sealed_filing is not None
    assert sealed_filing.is_sealed is True

    # 1. Clerk evaluation (Clearance: STANDARD) -> Redacted
    clerk_dict, is_redacted, reason = evaluate_filing_access(
        sealed_filing.to_dict(),
        role=Role.CLERK.value,
        clearance_level=ClearanceLevel.STANDARD.value,
        user_id="clerk-001"
    )
    assert is_redacted is True
    assert clerk_dict["raw_text"] == SEALED_REDACTION_NOTICE
    assert "CJIS Rule 5.9" in reason

    # 2. Public evaluation -> Redacted
    public_dict, is_redacted_pub, _ = evaluate_filing_access(
        sealed_filing.to_dict(),
        role=Role.PUBLIC.value,
        clearance_level=ClearanceLevel.STANDARD.value,
        user_id="public-visitor"
    )
    assert is_redacted_pub is True
    assert public_dict["raw_text"] == SEALED_REDACTION_NOTICE

    # 3. Chief Judge evaluation -> Unredacted In Camera Access
    judge_dict, is_redacted_judge, reason_judge = evaluate_filing_access(
        sealed_filing.to_dict(),
        role=Role.CHIEF_JUDGE.value,
        clearance_level=ClearanceLevel.JUDICIAL_RESTRICTED.value,
        user_id="judge-carter"
    )
    assert is_redacted_judge is False
    assert "DOB: 05/14/2016" in judge_dict["raw_text"]
    assert judge_dict["_access_level"] == "UNRESTRICTED_JUDICIAL_IN_CAMERA"


def test_cryptographic_audit_ledger_chain_and_tamper_detection(test_db):
    """
    Verifies that all audit logs form a continuous SHA-256 chain and any tampering is flagged.
    """
    # Record two new state events
    entry1 = CryptographicAuditLedger.record_db_event(
        db=test_db,
        case_id="2026-CV-012345",
        filing_id="filing-001",
        event_type="CLERK_DEFICIENCY_ISSUED",
        operator_id="clerk-007",
        decision_payload={"defects_noted": 2},
        model_version="gemini-2.5-flash",
        prompt_hash="abc123hash",
        decision="DEFICIENT",
        clerk_override={"action": "ISSUE_DEFICIENCY", "notes": "Missing sig"},
    )
    assert entry1.entry_id > 1

    entry2 = CryptographicAuditLedger.record_db_event(
        db=test_db,
        case_id="2026-CV-012345",
        filing_id="filing-001",
        event_type="JUDICIAL_REVIEW_INITIATED",
        operator_id="judge-carter",
        decision_payload={"review_type": "EXPEDITED"},
        model_version="gemini-2.5-flash",
        prompt_hash="xyz789hash",
        decision="REVIEW",
    )
    assert entry2.previous_hash == entry1.current_hash

    # Verify chain integrity
    verification = CryptographicAuditLedger.verify_chain_db(test_db)
    assert verification["verified"] is True
    assert verification["total_records"] >= 3

    # Tamper test: Alter entry1 hash directly in database
    entry1.decision = "UNAUTHORIZED_TAMPERED_DECISION"
    test_db.commit()

    tamper_result = CryptographicAuditLedger.verify_chain_db(test_db)
    assert tamper_result["verified"] is False
    assert "Cryptographic signature mismatch" in tamper_result["error"]


def test_api_get_filings_rbac_and_audit(client, test_db):
    """Verifies GET /filings RBAC redaction and audit telemetry through FastAPI."""
    # Request as CLERK
    res_clerk = client.get("/filings", headers={"X-Court-Role": "CLERK", "X-Court-Clearance": "STANDARD"})
    assert res_clerk.status_code == 200
    filings = res_clerk.json()
    assert len(filings) == 6

    # Check filing-003 is redacted for clerk
    f003_clerk = next(f for f in filings if f["id"] == "filing-003")
    assert f003_clerk["is_sealed"] is True
    assert f003_clerk["raw_text"] == SEALED_REDACTION_NOTICE

    # Request as CHIEF_JUDGE
    res_judge = client.get("/filings", headers={"X-Court-Role": "CHIEF_JUDGE", "X-Court-Clearance": "SEALED_CONFIDENTIAL"})
    assert res_judge.status_code == 200
    f003_judge = next(f for f in res_judge.json() if f["id"] == "filing-003")
    assert f003_judge["raw_text"] != SEALED_REDACTION_NOTICE
    assert "Jonathan Vance" in f003_judge["raw_text"]

    # Verify audit trail contains sealed record access events
    res_audit = client.get("/audit/trail")
    assert res_audit.status_code == 200
    audit_records = res_audit.json()
    event_types = [a["event_type"] for a in audit_records]
    assert "SEALED_RECORD_ACCESS_REDACTED" in event_types
    assert "SEALED_RECORD_IN_CAMERA_ACCESS_GRANTED" in event_types


def test_api_clerk_adjudicate_override(client, test_db):
    """Verifies clerk override endpoint updates filing status and records audit record."""
    override_payload = {
        "case_number": "2026-CV-012345",
        "filing_id": "filing-001",
        "clerk_id": "clerk-senior-42",
        "action": "APPROVE_OVERRIDE",
        "decision_notes": "Attorney confirmed wet ink scan submitted via facsimile.",
        "relief_designation": "DISCOVERY_COMPEL",
        "override_reason": "Good cause shown",
        "model_version": "gemini-2.5-flash",
        "prompt_hash": "prompthash123",
    }
    res = client.post("/filings/clerk-adjudicate", json=override_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CLERK_ACTION_RECORDED"

    # Verify filing updated in DB
    filing = test_db.query(FilingModel).filter(FilingModel.id == "filing-001").first()
    assert filing.workflow_status == "VALIDATED"
    assert filing.docket_status == "VALIDATED"
    assert filing.clerk_decision["clerk_id"] == "clerk-senior-42"

    # Verify audit chain verification endpoint
    res_verify = client.get("/audit/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["verified"] is True
