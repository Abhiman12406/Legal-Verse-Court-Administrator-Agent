"""
Database Seeder for LexisOps ACID Case Records and Docket Filings.
Populates standard benchmark filings (filing-001 through filing-006) and genesis audit entries.
"""

import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from lexis_ops.db.models import CaseModel, FilingModel, AuditLogModel


CASES_SEED = [
    {
        "case_number": "2026-CV-012345",
        "case_title": "Acme Corporation v. Global Dynamics LLC",
        "court_division": "CIVIL DIVISION - COMMERCIAL",
        "assigned_judge_id": "HON. ELENA CARTER",
        "case_type": "CIVIL",
        "is_sealed": False,
    },
    {
        "case_number": "2026-CV-887711",
        "case_title": "Mary Wilson v. Metropolis Housing Corp",
        "court_division": "HOUSING & EMERGENCY SESSIONS",
        "assigned_judge_id": "HON. MARCUS VANCE",
        "case_type": "EMERGENCY_HOUSING",
        "is_sealed": False,
    },
    {
        "case_number": "2026-JU-000492",
        "case_title": "In the Matter of Minor Child Jonathan Vance",
        "court_division": "FAMILY & JUVENILE COURT",
        "assigned_judge_id": "HON. SARAH LIN",
        "case_type": "JUVENILE_CONFIDENTIAL",
        "is_sealed": True,
    },
    {
        "case_number": "2026-CV-099211",
        "case_title": "Sterling Logistics Inc. v. Apex Railroad Corp.",
        "court_division": "CIVIL DIVISION - GENERAL",
        "assigned_judge_id": "HON. ELENA CARTER",
        "case_type": "CIVIL",
        "is_sealed": False,
    },
    {
        "case_number": "2026-CV-003418",
        "case_title": "Metropolis Realty Group v. Carlos Gomez",
        "court_division": "HOUSING & TENANT ASSISTANCE",
        "assigned_judge_id": "HON. SARAH LIN",
        "case_type": "PRO_SE_HOUSING",
        "is_sealed": False,
    },
]

FILINGS_SEED = [
    {
        "id": "filing-001",
        "case_number": "2026-CV-012345",
        "case_id": "c100-2026-cv-012345",
        "court_division": "CIVIL DIVISION - COMMERCIAL",
        "assigned_judge_id": "HON. ELENA CARTER",
        "document_title": "PLAINTIFF'S MOTION TO COMPEL DISCOVERY RESPONSES",
        "party_type": "PLAINTIFF",
        "filing_date": "2026-09-04",
        "is_emergency": False,
        "is_sealed": False,
        "severity_level": "SEV-2",
        "workflow_status": "AWAITING_CLERK",
        "docket_status": "CONDITIONALLY_LODGED",
        "cure_deadline": "2026-09-18",
        "lodged_receipt_timestamp": "2026-09-04T12:00:00.104291Z",
        "conflict_screen_passed": True,
        "extraction_confidence": 0.94,
        "signature_detected": False,
        "certificate_of_service_valid": False,
        "defects": [
            {
                "rule_citation": "Local Civil Rule 11.1",
                "defect_description": "Missing Signature Block: Submission lacks wet-ink scan, digital cryptographic signature, or recognized /s/ attorney notation.",
                "severity": "MANDATORY_REJECT",
                "page_reference": 2,
            },
            {
                "rule_citation": "Local Civil Rule 5.2(b)",
                "defect_description": "Missing Certificate of Service: Filings must verify transmission method and service addresses to all active counsel.",
                "severity": "MANDATORY_REJECT",
                "page_reference": 2,
            },
        ],
        "raw_text": (
            "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
            "COUNTY OF METROPOLIS\n\n"
            "CASE NO: 2026-CV-012345\n"
            "DIVISION: CIVIL COMMERCIAL\n\n"
            "ACME CORPORATION,\n    Plaintiff,\nv.\nGLOBAL DYNAMICS LLC,\n    Defendant.\n\n"
            "PLAINTIFF'S MOTION TO COMPEL DISCOVERY RESPONSES\n\n"
            "Plaintiff Acme Corporation respectfully moves this Court for an Order compelling Defendant Global Dynamics LLC to provide full and unredacted answers to Plaintiff's First Set of Interrogatories and Requests for Production of Documents served on July 10, 2026.\n\n"
            "Good cause exists because depositions are scheduled to commence in three weeks, and Defendant has failed to tender statutory disclosures or privilege logs.\n\n"
            "WHEREFORE, Plaintiff prays that this Court enter an Order compelling production within ten (10) calendar days.\n\n"
            "[DEFECT ALERT: No signature block provided]\n"
            "[DEFECT ALERT: No Certificate of Service attached]"
        ),
    },
    {
        "id": "filing-002",
        "case_number": "2026-CV-887711",
        "case_id": "c200-2026-cv-887711",
        "court_division": "HOUSING & EMERGENCY SESSIONS",
        "assigned_judge_id": "HON. MARCUS VANCE",
        "document_title": "EMERGENCY EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER AND STAY OF WRIT",
        "party_type": "PRO_SE",
        "filing_date": "2026-09-04",
        "is_emergency": True,
        "is_sealed": False,
        "severity_level": "SEV-1",
        "workflow_status": "AWAITING_CLERK",
        "docket_status": "CONDITIONALLY_LODGED",
        "is_ex_parte_tro": True,
        "rule_65b_notice_certified": False,
        "extraction_confidence": 0.91,
        "signature_detected": True,
        "certificate_of_service_valid": False,
        "defects": [
            {
                "rule_citation": "Fed. R. Civ. P. 65(b)(1)(B)",
                "defect_description": "Missing Attorney Notice Certification: Emergency ex parte TRO application lacks written certification detailing efforts made to give notice or reasons notice should not be required (Granny Goose Foods v. Teamsters).",
                "severity": "EMERGENCY_HALT",
                "page_reference": 1,
            },
            {
                "rule_citation": "Emergency Directive 2026-01",
                "defect_description": "Immediate Judicial Intervention Required: Ex Parte Temporary Restraining Order with active writ execution within 24 hours.",
                "severity": "EMERGENCY_HALT",
                "page_reference": 1,
            },
            {
                "rule_citation": "Local Civil Rule 5.2(b)",
                "defect_description": "Incomplete Certificate of Service: Notice not transmitted to Landlord's designated process agent.",
                "severity": "CURABLE_MINOR",
                "page_reference": 1,
            },
        ],
        "raw_text": (
            "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
            "CASE NO: 2026-CV-887711\n\n"
            "MARY WILSON,\n    Plaintiff Pro Se,\nv.\nMETROPOLIS HOUSING CORP,\n    Defendant.\n\n"
            "EMERGENCY EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER AND STAY OF WRIT OF RESTITUTION\n\n"
            "I, Mary Wilson, representing myself pro se, respectfully petition this Court for an immediate emergency order staying enforcement of the writ of eviction scheduled for execution tomorrow at 8:00 AM.\n\n"
            "I was not served with the 14-day notice to quit, and I have paid all rental arrears into the court registry account. Severe irreparable harm will result if my minor children and I are displaced without hearing.\n\n"
            "Respectfully submitted,\n/s/ Mary Wilson, Pro Se\nPhone: (555) 019-2834"
        ),
    },
    {
        "id": "filing-003",
        "case_number": "2026-JU-000492",
        "case_id": "c300-2026-ju-000492",
        "court_division": "FAMILY & JUVENILE COURT",
        "assigned_judge_id": "HON. SARAH LIN",
        "document_title": "CONFIDENTIAL STATUS REPORT REGARDING MINOR CHILD",
        "party_type": "INTERVENOR",
        "filing_date": "2026-09-04",
        "is_emergency": False,
        "is_sealed": True,
        "severity_level": "SEV-1",
        "workflow_status": "HALTED_SECURITY",
        "docket_status": "CONDITIONALLY_LODGED",
        "extraction_confidence": 0.82,
        "signature_detected": True,
        "certificate_of_service_valid": True,
        "defects": [
            {
                "rule_citation": "CJIS/FedRAMP Rule 5.9",
                "defect_description": "SEALED_RECORD_DETECTED: Case is sealed juvenile proceeding. Text prohibited from general LLM ingress. Unredacted SSN detected: 123-45-6789.",
                "severity": "EMERGENCY_HALT",
                "page_reference": 1,
            },
        ],
        "raw_text": (
            "[CONFIDENTIAL COURT RECORD - RESTRICTED ACCESS]\n"
            "IN THE JUVENILE DIVISION OF THE METROPOLIS TRIAL COURT\n"
            "CASE NO: 2026-JU-000492\n\n"
            "IN THE MATTER OF:\n"
            "Minor Child Jonathan Vance (DOB: 05/14/2016)\n"
            "Subject SSN: 123-45-6789\n\n"
            "CASEWORKER PROGRESS EVALUATION REPORT\n"
            "Submitted by County Department of Children & Family Services.\n"
            "*** AUTOMATIC PIPELINE HALT: UNREDACTED JUVENILE PII & SEALED RECORD DETECTED ***"
        ),
    },
    {
        "id": "filing-004",
        "case_number": "2026-CV-099211",
        "case_id": "c400-2026-cv-099211",
        "court_division": "CIVIL DIVISION - GENERAL",
        "assigned_judge_id": "HON. ELENA CARTER",
        "document_title": "JOINT STIPULATION FOR EXTENSION OF TIME TO FILE OPPOSITION",
        "party_type": "DEFENDANT",
        "filing_date": "2026-09-04",
        "is_emergency": False,
        "is_sealed": False,
        "severity_level": "CLEAN",
        "workflow_status": "COMPLETED",
        "docket_status": "VALIDATED",
        "conflict_screen_passed": True,
        "conflicted_judges_excluded": ["HON. MARCUS VANCE"],
        "extraction_confidence": 0.99,
        "signature_detected": True,
        "certificate_of_service_valid": True,
        "defects": [],
        "scheduled_slot": {
            "hearing_id": "slot-99211-a",
            "case_number": "2026-CV-099211",
            "courtroom_id": "CR-101",
            "assigned_judge_id": "HON. ELENA CARTER",
            "scheduled_date": "2026-09-28",
            "start_time": "09:30:00",
            "duration_minutes": 60,
            "interpreter_locked": True,
            "status": "CONFIRMED",
        },
        "generated_notice": {
            "notice_type": "NOTICE_OF_HEARING",
            "title": "Notice of Formal Hearing - Case 2026-CV-099211",
            "body_text": "PLEASE TAKE NOTICE that a hearing has been calendarized in Courtroom CR-101 before Hon. Elena Carter on September 28, 2026 at 09:30 AM Local Time.",
        },
        "raw_text": (
            "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
            "CASE NO: 2026-CV-099211\n\n"
            "STERLING LOGISTICS INC.,\n    Plaintiff,\nv.\nAPEX RAILROAD CORP.,\n    Defendant.\n\n"
            "JOINT STIPULATION FOR EXTENSION OF TIME\n\n"
            "The parties jointly move to enlarge time for filing Defendant's Opposition by fourteen (14) days.\n"
            "Good cause exists due to complex multi-state carrier records review.\n\n"
            "Respectfully submitted,\n/s/ Robert Vance, Esq. (Counsel for Defendant)\n/s/ Amanda Cruz, Esq. (Counsel for Plaintiff)\n\n"
            "CERTIFICATE OF SERVICE\nI certify that a true copy was served electronically via ECF upon all registered attorneys on Sept 4, 2026.\n/s/ Robert Vance, Esq."
        ),
    },
    {
        "id": "filing-005",
        "case_number": "2026-CV-003418",
        "case_id": "c500-2026-cv-003418",
        "court_division": "HOUSING & TENANT ASSISTANCE",
        "assigned_judge_id": "HON. SARAH LIN",
        "document_title": "UNCLASSIFIED PRO SE SUBMISSION (QUARANTINED - UNSTRUCTURED)",
        "party_type": "PRO_SE",
        "filing_date": "2026-09-04",
        "is_emergency": False,
        "is_sealed": False,
        "severity_level": "SEV-3: UNSTRUCTURED_PRO_SE",
        "workflow_status": "AWAITING_CLERK",
        "docket_status": "CONDITIONALLY_LODGED",
        "cure_deadline": "FROZEN_PENDING_IFP_RULING",
        "is_ifp_pending": True,
        "ifp_detected": True,
        "extraction_confidence": 0.64,
        "signature_detected": True,
        "certificate_of_service_valid": False,
        "pro_se_quarantined": True,
        "defects": [
            {
                "rule_citation": "Administrative Directive 2026-04(b)",
                "defect_description": "Unstructured Pro Se Pleading Quarantined: Extraction confidence (64.0%) falls below required 70.0% threshold. Automated notice generation suspended pending clerk relief designation.",
                "severity": "SEV-3: UNSTRUCTURED_PRO_SE",
                "page_reference": 1,
            },
            {
                "rule_citation": "Local Civil Rule 5.2(b)",
                "defect_description": "Missing Certificate of Service: Informal pro se pleading does not specify delivery or transmission to opposing landlord or counsel.",
                "severity": "CURABLE_MINOR",
                "page_reference": 1,
            },
        ],
        "raw_text": (
            "TO THE METROPOLIS TRIAL COURT CLERK:\n"
            "CASE NUMBER: 2026-CV-003418\n\n"
            "I am writing because I cannot afford the filing fee of $250. My income this month was zero due to medical disability and I am in danger of being displaced. I need the court to waive my fees so I can file my answer to the landlord's lawsuit.\n\n"
            "Also I ask for 30 more days to respond because I need an interpreter who speaks Spanish and legal aid appointment next week. Please stop them from locking me out of my apartment before I can see the judge.\n\n"
            "Thank you,\n/s/ Carlos Gomez\nCarlos Gomez, Defendant Pro Se\nPhone: (555) 321-9988"
        ),
    },
    {
        "id": "filing-006",
        "case_number": "2026-CV-003418",
        "case_id": "c500-2026-cv-003418",
        "court_division": "HOUSING & TENANT ASSISTANCE",
        "assigned_judge_id": "HON. SARAH LIN",
        "document_title": "PRO SE ELECTION RETURN FORM: AFFIRMED (CASTRO V. UNITED STATES)",
        "party_type": "PRO_SE",
        "filing_date": "2026-09-04",
        "is_emergency": False,
        "is_sealed": False,
        "severity_level": "CLEAN",
        "workflow_status": "VALIDATED",
        "docket_status": "VALIDATED",
        "extraction_confidence": 0.98,
        "signature_detected": True,
        "certificate_of_service_valid": True,
        "is_castro_response": True,
        "castro_tracking_token": "CASTRO-RECLASS-2026-CV-003418-filing-005",
        "castro_election": "AFFIRM",
        "defects": [],
        "raw_text": (
            "IN THE DISTRICT COURT OF THE FIRST JUDICIAL DISTRICT\n"
            "TRACKING TOKEN: CASTRO-RECLASS-2026-CV-003418-filing-005\n"
            "CASE NO: 2026-CV-003418\n\n"
            "PRO SE LITIGANT ELECTION RESPONSE FORM\n"
            "Pursuant to Castro v. United States, 540 U.S. 375 (2003)\n\n"
            "[X] OPTION 1: AFFIRM & PROCEED\n"
            "    I consent to the Court recharacterizing my submission as a formal Petition for In Forma Pauperis (Fee Waiver)\n"
            "    and request that the Court adjudicate it as currently drafted.\n\n"
            "[ ] OPTION 2: AMEND TO ADD CLAIMS\n"
            "[ ] OPTION 3: WITHDRAW WITHOUT PREJUDICE\n\n"
            "Date: September 4, 2026\n/s/ Carlos Gomez\nCarlos Gomez, Defendant Pro Se"
        ),
    },
]


def seed_db(db: Session, force: bool = False):
    """
    Seeds cases, filings, and genesis audit record if database is empty or force=True.
    """
    existing_filings_count = db.query(FilingModel).count()
    if existing_filings_count > 0 and not force:
        return {"status": "ALREADY_SEEDED", "filings_count": existing_filings_count}

    if force:
        db.query(AuditLogModel).delete()
        db.query(FilingModel).delete()
        db.query(CaseModel).delete()
        db.commit()

    # 1. Seed Cases
    for case_data in CASES_SEED:
        case_obj = CaseModel(**case_data)
        db.merge(case_obj)
    db.commit()

    # 2. Seed Filings
    for filing_data in FILINGS_SEED:
        filing_obj = FilingModel(**filing_data)
        db.merge(filing_obj)
    db.commit()

    # 3. Seed Genesis Audit Chain
    from lexis_ops.security.audit_ledger import CryptographicAuditLedger

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
    genesis_prompt = "LEXISOPS_GENESIS_SYSTEM_PROMPT_v1.0"
    genesis_prompt_hash = hashlib.sha256(genesis_prompt.encode("utf-8")).hexdigest()
    genesis_timestamp = datetime.now(timezone.utc).isoformat()
    
    genesis_payload = {
        "event": "DATABASE_GENESIS_ACID_INITIALIZATION",
        "cases_initialized": len(CASES_SEED),
        "filings_initialized": len(FILINGS_SEED),
        "standards": ["FED_R_CIV_P_5d4", "CJIS_5.9", "CASTRO_540_US_375", "28_USC_1915"]
    }
    
    genesis_current_hash = CryptographicAuditLedger.compute_entry_hash(
        previous_hash=GENESIS_HASH,
        timestamp=genesis_timestamp,
        case_id="SYSTEM-GENESIS-2026",
        filing_id="filing-genesis-000",
        event_type="GENESIS_IMMUTABLE_ROOT",
        operator_id="SYSTEM_ROOT",
        decision_payload=genesis_payload,
        model_version="gemini-2.5-flash",
        prompt_hash=genesis_prompt_hash,
        decision="GENESIS_SEED_INITIALIZED",
        clerk_override=None,
    )

    genesis_entry = AuditLogModel(
        timestamp=genesis_timestamp,
        case_id="SYSTEM-GENESIS-2026",
        filing_id="filing-genesis-000",
        model_version="gemini-2.5-flash",
        prompt_hash=genesis_prompt_hash,
        decision="GENESIS_SEED_INITIALIZED",
        clerk_override=None,
        agent_version="lexis-ops-v2.0-acid",
        event_type="GENESIS_IMMUTABLE_ROOT",
        operator_id="SYSTEM_ROOT",
        decision_payload=genesis_payload,
        previous_hash=GENESIS_HASH,
        current_hash=genesis_current_hash,
    )
    db.add(genesis_entry)
    db.commit()

    return {
        "status": "SEEDED_SUCCESSFULLY",
        "cases_seeded": len(CASES_SEED),
        "filings_seeded": len(FILINGS_SEED),
        "genesis_hash": genesis_current_hash,
    }
