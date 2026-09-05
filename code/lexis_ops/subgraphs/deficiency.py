from __future__ import annotations

from typing import List
from lexis_ops.schemas.state import ProposedOrderToStrike, CastroRecharacterizationNotice


def generate_proposed_order_to_strike(
    case_number: str,
    filing_title: str,
    defects_cited: List[str],
    cure_expired_date: str,
    court_division: str = "CIVIL DIVISION",
) -> ProposedOrderToStrike:
    """
    Automated generation of [Proposed] Order to Strike Non-Conforming Pleading.
    Under Fed. R. Civ. P. 5(d)(4) and Loya v. Desert Sands, 721 F.2d 279,
    a clerk of court cannot unilaterally refuse or strike a filing.
    When the 14-day statutory cure period lapses without cure, the system
    compiles this formal Proposed Order for Article III judicial execution.
    """
    defects_bulleted = "\n".join(f"  • {defect}" for defect in defects_cited)

    order_text = f"""IN THE DISTRICT COURT OF THE FIRST JUDICIAL DISTRICT
{court_division}

CASE NO: {case_number}

[PROPOSED] ORDER TO STRIKE NON-CONFORMING PLEADING

THIS MATTER having come before the Court upon the expiration of the statutory
fourteen (14) day cure period pursuant to Local Civil Rule 5.4 and Fed. R. Civ. P. 5(d)(4),
concerning the submission entitled:

    "{filing_title}"

The Court finds that said pleading was conditionally lodged with the Court, and a formal
Notice of Procedural Deficiency was duly issued detailing the following non-conforming defects:

{defects_bulleted}

The record establishes that the fourteen (14) day statutory cure period expired on
{cure_expired_date}, and the filing party has failed to submit a curative amended pleading
or motion for extension of time. Pursuant to Local Civil Rule 11.1 and the inherent power
of this Court to manage its docket:

IT IS HEREBY ORDERED:
1. The pleading entitled "{filing_title}" is STRICKEN from the active docket without prejudice.
2. The Clerk of Court shall register this Order in the official electronic case record
   and transmit formal notice to all counsel of record and self-represented parties.

SO ORDERED.

DATED: _________________________
                                    ____________________________________
                                    HONORABLE PRESIDING JUDGE
                                    (Cryptographic HMAC Signature Required)
"""

    return ProposedOrderToStrike(
        case_number=case_number,
        filing_title=filing_title,
        defects_cited=defects_cited,
        cure_expired_date=cure_expired_date,
        order_text=order_text,
        proposed_by="SYSTEM_DOCKET_ENGINE",
        requires_judicial_hmac=True,
    )


def generate_castro_recharacterization_notice(
    case_number: str,
    filing_id: str,
    original_filing_title: str,
    received_date: str,
    proposed_recharacterization: str,
    court_division: str = "CIVIL DIVISION",
) -> CastroRecharacterizationNotice:
    """
    Automated compilation of formal Castro Warning & 14-Day Statutory Election Form.
    Under Castro v. United States, 540 U.S. 375 (2003), a court cannot recharacterize
    a pro se litigant's informal pleading into a formal motion without:
    1. Notifying the litigant of its intent to recharacterize;
    2. Warning of preclusive legal consequences (second or successive motion bar, res judicata, forfeiture of claims);
    3. Providing a statutory opportunity to affirm, amend, or withdraw the pleading within 14 days;
    4. Embedding a machine-readable tracking token for automated docket linkage.
    """
    from datetime import date, timedelta

    try:
        base_d = date.fromisoformat(received_date)
    except Exception:
        base_d = date.today()

    election_deadline = (base_d + timedelta(days=14)).isoformat()
    castro_tracking_token = f"CASTRO-RECLASS-{case_number}-{filing_id}"

    notice_text = f"""IN THE DISTRICT COURT OF THE FIRST JUDICIAL DISTRICT
{court_division}

CASE NO: {case_number}
FILING REF: {filing_id}
TRACKING TOKEN: {castro_tracking_token}

FORMAL NOTICE OF INTENT TO RECHARACTERIZE PRO SE PLEADING
AND MANDATORY CASTRO WARNING ADVISORY
(Pursuant to Castro v. United States, 540 U.S. 375 (2003))

TO THE SELF-REPRESENTED (PRO SE) LITIGANT:

PLEASE TAKE NOTICE that on {received_date}, you submitted a document entitled:
    "{original_filing_title}"

The Court, having reviewed your informal submission, proposes to RECHARACTERIZE said
pleading as a formal:
    "{proposed_recharacterization}"

================================================================================
MANDATORY WARNING OF PRECLUSIVE LEGAL CONSEQUENCES UNDER CASTRO V. UNITED STATES
================================================================================
Under the United States Supreme Court's binding decision in Castro v. United States, 540 U.S. 375 (2003),
you are hereby cautioned that recharacterizing your informal pleading into a formal motion has serious
legal and procedural consequences:

1. SECOND OR SUCCESSIVE RESTRICTIONS & PRECLUSION:
   If this pleading is recharacterized as a formal motion, any future motions or claims addressing the
   same subject matter, transaction, conviction, or adverse action may be legally barred under the
   doctrines of res judicata, collateral estoppel, or statutory restrictions on second or successive motions.

2. FORFEITURE OF UNASSERTED GROUNDS:
   Any claims, legal theories, or grounds for relief not expressly stated in this pleading may be deemed
   waived or procedurally defaulted for all future proceedings in this Court.

================================================================================
FOURTEEN (14) DAY STATUTORY ELECTION RETURN FORM
================================================================================
You have fourteen (14) calendar days from the date of this notice—until {election_deadline}—to
elect one of the following three statutory options by returning this form or filing a written election.
INCLUDE THE TRACKING TOKEN BELOW ON ANY SUBMISSION:

TRACKING TOKEN: {castro_tracking_token}

[ ] OPTION 1: AFFIRM & PROCEED
    I consent to the Court recharacterizing my submission as a formal {proposed_recharacterization}
    and request that the Court adjudicate it as currently drafted.

[ ] OPTION 2: AMEND TO ADD CLAIMS
    I intend to file an Amended Formal Pleading containing all grounds for relief, evidence, and legal
    arguments within fourteen (14) days.

[ ] OPTION 3: WITHDRAW WITHOUT PREJUDICE
    I elect to WITHDRAW this submission without prejudice to avoid preclusive legal consequences.

RETURN INSTRUCTIONS:
File this completed form with the Clerk of Court or e-file via the portal. Ensure the header token
"{castro_tracking_token}" is prominently displayed on the first page for automated docket linking.
"""

    return CastroRecharacterizationNotice(
        case_number=case_number,
        filing_id=filing_id,
        original_filing_title=original_filing_title,
        received_date=received_date,
        proposed_recharacterization=proposed_recharacterization,
        castro_tracking_token=castro_tracking_token,
        election_deadline=election_deadline,
        notice_text=notice_text,
        election_options=["AFFIRM", "AMEND", "WITHDRAW"],
        status="PENDING_ELECTION",
    )
