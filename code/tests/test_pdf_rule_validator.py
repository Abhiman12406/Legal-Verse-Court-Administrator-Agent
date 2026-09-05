import io
import pytest
from fastapi.testclient import TestClient

from lexis_ops.pdf_rule_validator import PDFRuleValidator, validate_pdf_rules
from lexis_ops.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_validate_pdf_clean_compliant_filing():
    """Verifies that a fully compliant pleading passes all statutory rules."""
    text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-099211\n"
        "DIVISION: GENERAL CIVIL\n\n"
        "STERLING LOGISTICS INC., Plaintiff\n"
        "v.\n"
        "APEX RAILROAD CORP., Defendant\n\n"
        "JOINT STIPULATION FOR EXTENSION OF TIME\n\n"
        "The parties respectfully move this Court to enlarge the deadline for filing Defendant's Opposition.\n"
        "Good cause exists due to multi-state carrier record audits.\n\n"
        "Respectfully submitted,\n"
        "/s/ Amanda Cruz, Esq.\n"
        "Counsel for Plaintiff\n\n"
        "CERTIFICATE OF SERVICE\n"
        "I hereby certify that a true and correct copy was served electronically via ECF upon all registered counsel.\n"
        "/s/ Amanda Cruz, Esq."
    )
    result = validate_pdf_rules(text, filename="stipulation_extension.pdf")

    assert result.is_valid is True
    assert result.severity_level == "CLEAN"
    assert result.requires_clerk_review is False
    assert result.workflow_status == "VALIDATED"
    assert result.has_signature is True
    assert result.has_certificate_of_service is True
    assert result.has_formal_caption is True
    assert result.case_number == "2026-CV-099211"
    assert len(result.procedural_defects) == 0
    assert result.security_cleared is True


def test_validate_pdf_missing_signature_defect():
    """Verifies that a filing missing a signature block triggers Rule 11.1 mandatory defect."""
    text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-012345\n\n"
        "ACME CORP v. BETA LLC\n\n"
        "MOTION TO COMPEL DISCOVERY\n"
        "Plaintiff moves to compel interrogatory answers.\n\n"
        "CERTIFICATE OF SERVICE\n"
        "Served upon counsel via email on Sept 4, 2026."
    )
    result = validate_pdf_rules(text, filename="motion_no_sig.pdf")

    assert result.is_valid is False
    assert result.has_signature is False
    assert result.severity_level == "SEV-2"
    assert result.requires_clerk_review is True
    citations = [d.rule_citation for d in result.procedural_defects]
    assert "Local Civil Rule 11.1" in citations


def test_validate_pdf_missing_certificate_of_service_defect():
    """Verifies that a filing missing proof of service triggers Rule 5.2(b) mandatory defect."""
    text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-012345\n\n"
        "ACME CORP v. BETA LLC\n\n"
        "MOTION TO COMPEL DISCOVERY\n"
        "Plaintiff moves to compel interrogatory answers.\n\n"
        "Respectfully submitted,\n"
        "/s/ Jane Attorney, Esq."
    )
    result = validate_pdf_rules(text, filename="motion_no_service.pdf")

    assert result.is_valid is False
    assert result.has_certificate_of_service is False
    assert result.severity_level == "SEV-2"
    assert result.requires_clerk_review is True
    citations = [d.rule_citation for d in result.procedural_defects]
    assert "Local Civil Rule 5.2(b)" in citations


def test_validate_pdf_malformed_case_number():
    """Verifies that a non-standard case number format triggers Local Rule 3.1(a) caption defect."""
    text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: BAD-CASE-NUM-999\n\n"
        "PLAINTIFF'S STATUS REPORT\n\n"
        "Respectfully submitted,\n"
        "/s/ Jane Attorney, Esq.\n\n"
        "CERTIFICATE OF SERVICE\n"
        "Served upon counsel."
    )
    result = validate_pdf_rules(text, filename="bad_case.pdf")

    assert result.is_valid is False
    assert result.severity_level in ["SEV-2", "SEV-3", "SEV-3: UNSTRUCTURED_PRO_SE"]
    citations = [d.rule_citation for d in result.procedural_defects]
    assert "Local Rule 3.1(a)" in citations


def test_validate_pdf_emergency_motion():
    """Verifies that emergency motions trigger SEV-1 emergency escalation."""
    text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-887711\n\n"
        "EMERGENCY EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER\n"
        "Petitioner seeks an immediate stay of writ.\n\n"
        "Respectfully submitted,\n"
        "/s/ Mary Wilson, Pro Se\n\n"
        "CERTIFICATE OF SERVICE\n"
        "Served upon defendant."
    )
    result = validate_pdf_rules(text, filename="emergency_tro.pdf")

    assert result.is_emergency is True
    assert result.severity_level == "SEV-1"
    assert result.requires_clerk_review is True


def test_validate_pdf_sealed_and_pii_violation():
    """Verifies that unredacted SSN and sealed case status trigger CJIS/FedRAMP Rule 5.9 quarantine."""
    text = (
        "[CONFIDENTIAL COURT RECORD - FILED UNDER SEAL]\n"
        "IN THE JUVENILE DIVISION\n"
        "CASE NO: 2026-JU-000492\n\n"
        "Subject Minor Child Jonathan Vance (DOB: 05/14/2016)\n"
        "Social Security Number: 123-45-6789\n\n"
        "/s/ Social Worker Jane Doe\n"
        "CERTIFICATE OF SERVICE\n"
        "Served upon court guardian."
    )
    result = validate_pdf_rules(text, filename="sealed_juvenile.pdf")

    assert result.security_cleared is False
    assert result.is_sealed is True
    assert result.workflow_status == "HALTED_SECURITY"
    assert result.severity_level == "SEV-1"
    assert len(result.security_violations) > 0
    citations = [d.rule_citation for d in result.procedural_defects]
    assert "CJIS/FedRAMP Rule 5.9" in citations


def test_validate_pdf_unstructured_pro_se():
    """Verifies that informal pro se pleadings trigger SEV-3 pro se quarantine."""
    text = (
        "Dear Clerk of Court:\n"
        "I am writing pro se because I cannot pay the court fees and landlord wants to evict.\n"
        "/s/ Carlos Gomez"
    )
    result = validate_pdf_rules(text, filename="pro_se_letter.pdf")

    assert result.pro_se_quarantined is True
    assert result.severity_level == "SEV-3: UNSTRUCTURED_PRO_SE"
    assert result.requires_clerk_review is True
    citations = [d.rule_citation for d in result.procedural_defects]
    assert "Administrative Directive 2026-04(b)" in citations


def test_fastapi_upload_endpoint(client: TestClient):
    """Verifies that the FastAPI POST /filings/validate-pdf endpoint processes multipart PDF uploads."""
    content = (
        b"IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        b"CASE NO: 2026-CV-099211\n\n"
        b"JOINT STIPULATION FOR EXTENSION OF TIME\n\n"
        b"Respectfully submitted,\n"
        b"/s/ Amanda Cruz, Esq.\n\n"
        b"CERTIFICATE OF SERVICE\n"
        b"I hereby certify delivery upon all counsel.\n"
        b"/s/ Amanda Cruz, Esq."
    )
    files = {"file": ("test_stipulation.pdf", io.BytesIO(content), "application/pdf")}
    res = client.post("/filings/validate-pdf", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test_stipulation.pdf"
    assert data["case_number"] == "2026-CV-099211"
    assert data["is_valid"] is True
    assert data["severity_level"] == "CLEAN"
    assert data["has_signature"] is True
    assert data["has_certificate_of_service"] is True


def test_validate_binary_pdf_bytes_and_cli(tmp_path):
    """Verifies validation on physical binary PDF files and CLI subprocess execution."""
    import subprocess
    import sys
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-055123\n"
        "DIVISION: GENERAL CIVIL\n\n"
        "ACME CORP v. ZENITH LLC\n\n"
        "DEFENDANT'S ANSWER AND AFFIRMATIVE DEFENSES\n\n"
        "Defendant Zenith LLC answers the complaint and asserts affirmative defenses.\n\n"
        "Respectfully submitted,\n"
        "/s/ Marcus Vance, Esq.\n"
        "Counsel for Defendant\n\n"
        "CERTIFICATE OF SERVICE\n"
        "I hereby certify that a true copy was served electronically via ECF upon all registered counsel.\n"
        "/s/ Marcus Vance, Esq."
    )
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    # 1. Test binary bytes input
    res_bytes = validate_pdf_rules(pdf_bytes, filename="answer.pdf")
    assert res_bytes.is_valid is True
    assert res_bytes.case_number == "2026-CV-055123"
    assert res_bytes.severity_level == "CLEAN"

    # 2. Test physical file path input
    pdf_file = tmp_path / "answer.pdf"
    pdf_file.write_bytes(pdf_bytes)

    res_file = validate_pdf_rules(pdf_file)
    assert res_file.is_valid is True
    assert res_file.case_number == "2026-CV-055123"

    # 3. Test CLI execution
    cmd = [sys.executable, "-m", "lexis_ops.pdf_rule_validator", str(pdf_file), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    import json
    cli_data = json.loads(proc.stdout)
    assert cli_data["case_number"] == "2026-CV-055123"
    assert cli_data["is_valid"] is True
    assert cli_data["severity_level"] == "CLEAN"

