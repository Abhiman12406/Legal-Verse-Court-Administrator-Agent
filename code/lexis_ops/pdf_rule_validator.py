from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from lexis_ops.ingestion.ocr_parser import DoclingPDFParser, IngressFilingPayload
from lexis_ops.schemas.state import FilingPartyType, LexisOpsState, ProceduralDefect
from lexis_ops.security.gate import PreLLMSecurityGate
from lexis_ops.subgraphs.validation import deterministic_rule_engine_node


class PDFValidationResult(BaseModel):
    """
    Structured validation verdict resulting from PDF ingestion and statutory rule checks.
    """
    filename: str = Field(description="Original filename or document identifier")
    case_number: Optional[str] = Field(default=None, description="Extracted court case number standard YYYY-XX-XXXXXX")
    document_title: str = Field(description="Extracted or classified pleading title")
    filing_party_type: FilingPartyType = Field(default=FilingPartyType.PLAINTIFF)
    page_count: int = Field(default=1, ge=1)
    filing_date: str = Field(description="Ingress ISO date timestamp")
    
    # Ingestion Telemetry
    ingestion_mode: Literal["DIGITAL_SHORT_CIRCUIT", "NEURAL_OCR_DOCLING"] = "DIGITAL_SHORT_CIRCUIT"
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    ocr_latency_ms: float = Field(ge=0.0)
    has_embedded_text_layer: bool = True
    
    # Structural Verification Flags
    has_signature: bool = Field(description="Local Civil Rule 11.1 compliance")
    has_certificate_of_service: bool = Field(description="Local Civil Rule 5.2(b) compliance")
    has_formal_caption: bool = Field(description="Local Rule 3.1 formal caption compliance")
    is_emergency: bool = Field(default=False, description="SEV-1 emergency TRO/writ indicator")
    is_sealed: bool = Field(default=False, description="Confidential / sealed case status")
    security_cleared: bool = Field(default=True, description="Pre-LLM PII & juvenile record clearance")
    
    # 28 U.S.C. § 1915 IFP Indigency Tolling
    is_ifp_pending: bool = Field(default=False, description="28 U.S.C. § 1915 IFP fee waiver tolling active")
    ifp_detected: bool = Field(default=False, description="Form AO 240 or IFP petition detected")

    # Fed. R. Civ. P. 65(b)(1)(B) Ex Parte Emergency Injunction Gate
    is_ex_parte_tro: bool = Field(default=False, description="Whether filing is an emergency ex parte TRO application")
    rule_65b_notice_certified: Optional[bool] = Field(default=None, description="FRCP 65(b)(1)(B) notice certification verified")

    # Castro v. United States Pro Se Recharacterization & Token Ingress
    castro_token_detected: Optional[str] = Field(default=None, description="CASTRO-RECLASS tracking token detected on ingress")
    castro_parent_case_id: Optional[str] = Field(default=None, description="Parent case number parsed from CASTRO token")
    castro_parent_filing_id: Optional[str] = Field(default=None, description="Parent filing ID parsed from CASTRO token")
    castro_election: Optional[str] = Field(default=None, description="Parsed Castro election: AFFIRM, AMEND, or WITHDRAW")
    is_castro_response: bool = Field(default=False, description="Whether document is a returned Castro election form")

    # Procedural Outcome
    is_valid: bool = Field(description="True if filing passes all rules without mandatory defects or security halts")
    severity_level: str = Field(description="CLEAN, SEV-1, SEV-2, SEV-3, or SEV-3: UNSTRUCTURED_PRO_SE")
    requires_clerk_review: bool = Field(description="Whether filing requires manual clerk triage/override")
    workflow_status: str = Field(description="VALIDATED, AWAITING_CLERK, or HALTED_SECURITY")
    docket_status: str = Field(default="CONDITIONALLY_LODGED", description="Statutory status under FRCP 5(d)(4): VALIDATED, CONDITIONALLY_LODGED, HALTED_SECURITY")
    pro_se_quarantined: bool = Field(default=False, description="Whether filing is quarantined under pro se directive")
    lodged_receipt_timestamp: str = Field(default="", description="Microsecond-accurate RFC 3161 / ISO ingress timestamp")
    cure_deadline: Optional[str] = Field(default=None, description="Statutory 14-day cure deadline under Local Rule 5.4")
    
    # Defects & Violations
    procedural_defects: List[ProceduralDefect] = Field(default_factory=list)
    security_violations: List[str] = Field(default_factory=list)
    
    # Cryptographic Fingerprint
    audit_hash_sha256: str = Field(description="SHA-256 hash of extracted text/body for audit ledger chaining")

    raw_text_snippet: str = Field(description="Preview snippet of ingested document text")


class PDFRuleValidator:
    """
    Sovereign PDF Ingress & Procedural Rule Validation Engine.
    Executes multi-tier validation:
    1. Digital text short-circuit & neural OCR stream conversion
    2. Caption layout & confidence classification
    3. Pre-LLM Security Gating (SSN, juvenile PII, sealed cases)
    4. Deterministic Statutory Rule Engine (Rules 11.1, 5.2(b), 3.1, AD 2026-04)
    """

    @classmethod
    def validate_pdf(
        cls,
        file_input: Union[str, Path, bytes],
        filename: str = "filing.pdf",
        force_ocr: bool = False,
        filing_date: Optional[str] = None,
    ) -> PDFValidationResult:
        from datetime import date

        effective_date = filing_date or date.today().isoformat()

        # Handle Path objects
        if isinstance(file_input, Path):
            filename = file_input.name
            file_input = str(file_input)

        # 1. Ingest PDF and extract structural metadata
        ingress_payload: IngressFilingPayload = DoclingPDFParser.parse_pdf(
            file_input,
            filename=filename,
            force_ocr=force_ocr,
        )

        raw_text = ingress_payload.document_raw_text
        doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        metadata = ingress_payload.metadata

        # 2. Pre-LLM Security Gate (PII, SSN, Juvenile records, Sealed records)
        security_eval = PreLLMSecurityGate.evaluate(
            is_sealed=ingress_payload.is_sealed,
            raw_text=raw_text,
            case_type="CIVIL",
        )

        # 3. Assemble LangGraph-compatible state for Deterministic Rule Engine
        caption_layout = metadata.caption_layout
        party_type = (
            caption_layout.party_type
            if caption_layout
            else (
                FilingPartyType.PRO_SE
                if "PRO SE" in raw_text.upper()
                else FilingPartyType.PLAINTIFF
            )
        )

        # Check for 28 U.S.C. § 1915 IFP / Fee Waiver Petition
        combined_text = f"{filename} {ingress_payload.document_title} {raw_text}".lower()
        ifp_detected = bool(
            re.search(
                r"(?:form\s+ao\s*240|\bao\s*240\b|in\s+forma\s+pauperis|\bifp\b|fee\s+waiver|without\s+prepaying\s+fees|affidavit\s+of\s+indigency|fw-001)",
                combined_text,
            )
        )
        is_ifp_pending = ifp_detected

        # Check for FRCP 65(b)(1)(B) Emergency Ex Parte TRO Application
        is_ex_parte_tro = bool(
            ("ex parte" in combined_text and ("temporary restraining order" in combined_text or "tro" in combined_text or "stay" in combined_text or ingress_payload.emergency_motion))
            or (ingress_payload.emergency_motion and "ex parte" in combined_text)
            or ("ex parte motion" in combined_text)
        )
        is_emergency = bool(ingress_payload.emergency_motion or is_ex_parte_tro or "emergency" in combined_text)

        rule_65b_notice_certified: Optional[bool] = None
        if is_ex_parte_tro:
            # Rule 65(b)(1)(B) requires attorney certification in writing of notice efforts or reasons notice should not be required
            rule_65b_notice_certified = bool(
                re.search(
                    r"(?:65\s*\(\s*b\s*\)|notice\s+certification|certificate\s+of\s+counsel|certif(?:y|ies)\s+in\s+writing|efforts\s+made\s+to\s+give\s+notice|reasons\s+why\s+notice\s+should\s+not\s+be\s+required|immediate\s+and\s+irreparable\s+injury.*before\s+the\s+adverse\s+party\s+can\s+be\s+heard)",
                    raw_text.lower(),
                )
            )

        # Check for Castro v. United States Return Election Token: CASTRO-RECLASS-<case_id>-<filing_id>
        castro_token_match = re.search(r"CASTRO-RECLASS-([A-Za-z0-9\-_]+)", raw_text)
        castro_token_detected = None
        castro_parent_case_id = None
        castro_parent_filing_id = None
        castro_election = None
        is_castro_response = False

        if castro_token_match:
            castro_token_detected = castro_token_match.group(0)
            is_castro_response = True
            rest = castro_token_detected[len("CASTRO-RECLASS-"):]
            if "-filing-" in rest:
                case_part, filing_suffix = rest.split("-filing-", 1)
                castro_parent_case_id = case_part
                castro_parent_filing_id = f"filing-{filing_suffix}"
            elif "-" in rest:
                parts = rest.rsplit("-", 1)
                castro_parent_case_id = parts[0]
                castro_parent_filing_id = parts[1]
            else:
                castro_parent_case_id = rest
                castro_parent_filing_id = "filing-001"

            text_upper = raw_text.upper()
            if "[X] AFFIRM" in text_upper or "[X] CONSENT" in text_upper or "ELECTION: AFFIRM" in text_upper or "ELECT TO AFFIRM" in text_upper or "I AFFIRM" in text_upper or "OPTION 1: AFFIRM" in text_upper:
                castro_election = "AFFIRM"
            elif "[X] WITHDRAW" in text_upper or "ELECTION: WITHDRAW" in text_upper or "ELECT TO WITHDRAW" in text_upper or "I WITHDRAW" in text_upper or "OPTION 3: WITHDRAW" in text_upper:
                castro_election = "WITHDRAW"
            elif "[X] AMEND" in text_upper or "ELECTION: AMEND" in text_upper or "ELECT TO AMEND" in text_upper or "I AMEND" in text_upper or "OPTION 2: AMEND" in text_upper:
                castro_election = "AMEND"
            else:
                for opt in ["AFFIRM", "WITHDRAW", "AMEND"]:
                    if re.search(rf"\b{opt}\b", text_upper):
                        castro_election = opt
                        break

        state: LexisOpsState = {
            "filing_id": f"filing-{doc_hash[:8]}",
            "case_number": ingress_payload.case_number or "UNKNOWN-CASE-NO",
            "document_title": ingress_payload.document_title,
            "document_raw_text": raw_text,
            "filing_date": effective_date,
            "filing_party_type": party_type.value if hasattr(party_type, "value") else str(party_type),
            "page_count": metadata.page_count,
            "signature_detected": metadata.has_signature,
            "certificate_of_service_valid": metadata.has_certificate_of_service,
            "is_emergency": is_emergency,
            "is_sealed": ingress_payload.is_sealed,
            "extraction_confidence": metadata.confidence_score,
            "procedural_defects": [],
            "severity_level": "CLEAN",
            "requires_clerk_review": False,
            "workflow_status": "INGESTED",
            "audit_trail": [],
            "is_ifp_pending": is_ifp_pending,
            "ifp_detected": ifp_detected,
            "is_ex_parte_tro": is_ex_parte_tro,
            "rule_65b_notice_certified": rule_65b_notice_certified,
            "castro_token_detected": castro_token_detected,
            "castro_election": castro_election,
            "is_castro_response": is_castro_response,
        }

        # 4. Run Deterministic Rule Engine
        rule_output = deterministic_rule_engine_node(state)
        defects_dicts = rule_output.get("procedural_defects", [])
        severity_level = rule_output.get("severity_level", "CLEAN")
        requires_clerk = rule_output.get("requires_clerk_review", False)
        workflow_status = rule_output.get("workflow_status", "VALIDATED")
        is_pro_se_quarantined = rule_output.get("pro_se_quarantined", False)

        # Convert dict defects to typed Pydantic models
        procedural_defects: List[ProceduralDefect] = []
        for d in defects_dicts:
            if isinstance(d, ProceduralDefect):
                procedural_defects.append(d)
            elif isinstance(d, dict):
                procedural_defects.append(ProceduralDefect(**d))

        # Check FRCP 65(b)(1)(B) notice certification defect
        if is_ex_parte_tro and not rule_65b_notice_certified:
            severity_level = "SEV-1"
            requires_clerk = True
            procedural_defects.insert(
                0,
                ProceduralDefect(
                    rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
                    defect_description="Missing Attorney Notice Certification: Ex parte temporary restraining orders require attorney certification in writing of efforts to give notice or reasons notice should not be required under Rule 65(b)(1)(B) and Granny Goose Foods v. Teamsters, 415 U.S. 423.",
                    severity="EMERGENCY_HALT",  # type: ignore[arg-type]
                    page_reference=1,
                ),
            )

        # 5. Integrate Security Gate Findings
        security_violations = security_eval.pii_violations
        if not security_eval.cleared:
            severity_level = "SEV-1"
            requires_clerk = True
            workflow_status = "HALTED_SECURITY"
            procedural_defects.insert(
                0,
                ProceduralDefect(
                    rule_citation="CJIS/FedRAMP Rule 5.9",
                    defect_description="; ".join(security_violations) or "Unredacted SSN/juvenile PII or sealed record detected.",
                    severity="EMERGENCY_HALT",  # type: ignore[arg-type]
                    page_reference=1,
                ),
            )

        is_valid = (
            security_eval.cleared
            and severity_level == "CLEAN"
            and len(procedural_defects) == 0
            and not requires_clerk
        )

        has_formal_caption = (
            caption_layout.has_formal_caption if caption_layout else bool(ingress_payload.case_number)
        )

        snippet = raw_text[:400].strip() + ("..." if len(raw_text) > 400 else "")

        from datetime import datetime, timezone, timedelta
        receipt_ts = datetime.now(timezone.utc).isoformat()

        if not security_eval.cleared:
            docket_status = "HALTED_SECURITY"
            cure_deadline = None
        elif is_valid and not is_ifp_pending:
            docket_status = "VALIDATED"
            cure_deadline = None
        else:
            # Fed. R. Civ. P. 5(d)(4) & Loya v. Desert Sands: non-conforming filings are conditionally lodged
            docket_status = "CONDITIONALLY_LODGED"
            if is_ifp_pending:
                # 28 U.S.C. § 1915 & Williams-Guice: IFP petitions toll procedural deficiency/dismissal countdowns
                cure_deadline = "FROZEN_PENDING_IFP_RULING"
            else:
                try:
                    base_d = date.fromisoformat(effective_date)
                    cure_deadline = (base_d + timedelta(days=14)).isoformat()
                except Exception:
                    cure_deadline = (date.today() + timedelta(days=14)).isoformat()

        return PDFValidationResult(
            filename=filename,
            case_number=ingress_payload.case_number,
            document_title=ingress_payload.document_title,
            filing_party_type=party_type,
            page_count=metadata.page_count,
            filing_date=effective_date,
            ingestion_mode=metadata.ingestion_mode,
            extraction_confidence=round(metadata.confidence_score, 4),
            ocr_latency_ms=metadata.ocr_latency_ms,
            has_embedded_text_layer=metadata.has_embedded_text_layer,
            has_signature=metadata.has_signature,
            has_certificate_of_service=metadata.has_certificate_of_service,
            has_formal_caption=has_formal_caption,
            is_emergency=is_emergency,
            is_sealed=ingress_payload.is_sealed,
            security_cleared=security_eval.cleared,
            is_ifp_pending=is_ifp_pending,
            ifp_detected=ifp_detected,
            is_ex_parte_tro=is_ex_parte_tro,
            rule_65b_notice_certified=rule_65b_notice_certified,
            castro_token_detected=castro_token_detected,
            castro_parent_case_id=castro_parent_case_id,
            castro_parent_filing_id=castro_parent_filing_id,
            castro_election=castro_election,
            is_castro_response=is_castro_response,
            is_valid=is_valid,
            severity_level=severity_level,
            requires_clerk_review=requires_clerk,
            workflow_status=workflow_status,
            docket_status=docket_status,
            pro_se_quarantined=is_pro_se_quarantined,
            lodged_receipt_timestamp=receipt_ts,
            cure_deadline=cure_deadline,
            procedural_defects=procedural_defects,
            security_violations=security_violations,
            audit_hash_sha256=doc_hash,
            raw_text_snippet=snippet,
        )


def validate_pdf_rules(
    file_input: Union[str, Path, bytes],
    filename: str = "filing.pdf",
    force_ocr: bool = False,
    filing_date: Optional[str] = None,
) -> PDFValidationResult:
    """
    Convenience functional interface for PDF input and statutory rule validation.
    """
    return PDFRuleValidator.validate_pdf(
        file_input=file_input,
        filename=filename,
        force_ocr=force_ocr,
        filing_date=filing_date,
    )


def main():
    parser = argparse.ArgumentParser(
        description="LexisOps Sovereign PDF Ingress & Procedural Rule Validator"
    )
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to validate")
    parser.add_argument(
        "--force-ocr", action="store_true", help="Bypass digital text short-circuit and force Docling OCR"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON result"
    )

    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: File '{args.pdf_path}' not found.", file=sys.stderr)
        sys.exit(1)

    result = validate_pdf_rules(args.pdf_path, force_ocr=args.force_ocr)

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        status_color = "\033[92m" if result.is_valid else "\033[91m"
        reset_color = "\033[0m"
        print("=" * 70)
        print(" LEXISOPS COURT ADMINISTRATION: PDF RULE VALIDATION VERDICT")
        print("=" * 70)
        print(f"Filename:       {result.filename}")
        print(f"Case Number:    {result.case_number or 'NONE / UNKNOWN'}")
        print(f"Title:          {result.document_title}")
        print(f"Party:          {result.filing_party_type.value}")
        print(f"Ingestion Mode: {result.ingestion_mode} ({result.ocr_latency_ms} ms)")
        print(f"Confidence:     {result.extraction_confidence * 100:.1f}%")
        print(f"Signature:      {'PASSED' if result.has_signature else 'FAILED (Rule 11.1)'}")
        print(f"Cert of Serv:   {'PASSED' if result.has_certificate_of_service else 'FAILED (Rule 5.2b)'}")
        print(f"Caption:        {'PASSED' if result.has_formal_caption else 'INCOMPLETE'}")
        print("-" * 70)
        print(f"Verdict:        {status_color}{result.severity_level}{reset_color} ({result.workflow_status})")
        print(f"Clerk Review:   {'REQUIRED' if result.requires_clerk_review else 'NOT REQUIRED'}")
        print(f"Audit SHA-256:  {result.audit_hash_sha256}")
        if result.procedural_defects:
            print("-" * 70)
            print("CITED PROCEDURAL DEFECTS:")
            for idx, defect in enumerate(result.procedural_defects, 1):
                print(f"  {idx}. [{defect.rule_citation}] ({defect.severity}): {defect.defect_description}")
        if result.security_violations:
            print("-" * 70)
            print("SECURITY VIOLATIONS:")
            for v in result.security_violations:
                print(f"  - {v}")
        print("=" * 70)


if __name__ == "__main__":
    main()
