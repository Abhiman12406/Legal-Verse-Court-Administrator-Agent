# Scenario 02 — 28 U.S.C. § 1915 In Forma Pauperis (IFP) Fee Tolling

## Scenario summary

In Scenario 02, an indigent self-represented litigant submitted a civil rights complaint without paying the statutory $405 filing fee, attaching an application to proceed *In Forma Pauperis* (IFP) under 28 U.S.C. § 1915. The scenario tested whether the agent would recognize that an IFP filing tolls (pauses) automated dismissal timers, and whether the agent correctly establishes a mandatory 21-calendar-day fee tender grace period if the judicial officer denies the fee waiver.

## My prediction

I predicted that LexisOps would detect the missing fee code, match it with the attached financial affidavit, assign `IFP_APPLICATION_PENDING` status, and freeze all automatic procedural dismissal routines until judicial chambers acted on the application.

## What the participating agents did

* **Indigent Litigant Agent:** Ingested the civil rights complaint accompanied by financial declaration Form AO-240.
* **LexisOps (Court Clerk Agent):** Flagged missing filing fee, extracted the IFP application, placed the complaint into `TOLL_PENDING_IFP_RULING` status, and prevented automated case rejection.
* **Judicial Officer Agent:** Reviewed the applicant's financial affidavit, determined income exceeded statutory poverty guidelines, and entered an order denying IFP status.
* **LexisOps (Post-Ruling Workflow):** Calculated a 21-day statutory grace period from the date of denial, notified the litigant with exact payment instructions, and scheduled an automatic dismissal review only after the expiration of the 21-day window.

## Evidence from the episode

* **Audit Event:** `IFP_FEE_WAIVER_APPLICATION_DETECTED` with affidavit verification code `AO-240-CONFIRMED`.
* **Judicial Order Adjudication:** `POST /filings/ifp-adjudicate` executed with payload `{"action": "DENY", "judge_id": "JUDGE-CIVIL-02"}`.
* **Calculated Tolling Expiry:** Baseline date `2026-08-12` produced an active fee grace period ending `2026-09-02` (exactly 21 calendar days).

## Behavior of my agent

LexisOps handled statutory tolling deterministically. Rather than treating an unpaid filing as an immediate procedural defect justifying closure, it recognized that 28 U.S.C. § 1915 creates a substantive due process shield protecting access to the courts.

## Role adherence and decision quality

* **Role Adherence:** Perfect (10/10). The agent left the substantive financial determination of poverty entirely to the judge, executing only the procedural calendaring and timeline tolling.
* **Decision Quality:** High. Calculation of the 21-day grace period prevented premature administrative termination of an indigent party's constitutional claim.

## Information, uncertainty, and risk handling

* **Information Handled:** Fee waiver affidavit figures, poverty line schedules, and local rules governing payment deadlines.
* **Uncertainty:** Whether the applicant's reported income met the poverty threshold. LexisOps properly treated this as a judicial determination.
* **Risk Handling:** Minimized equal-protection and access-to-justice risks.

## Cooperation, disagreement, or influence

LexisOps coordinated cleanly between the litigant and judicial chambers. When a simulated automated docket maintenance script attempted to mark the case as "DELINQUENT_FEE_DISMISSAL", LexisOps blocked the script, citing the active IFP tolling flag.

## Unexpected or concerning behavior

None. The state transition from `TOLL_PENDING_IFP_RULING` to `IFP_DENIED_FEE_GRACE_PERIOD` was atomic and verified by the cryptographic audit trail.

## Alternative explanations

The clean handling of the 21-day tolling was reinforced by explicit statutory state models defined in Pydantic schemas rather than arbitrary prompt instructions.

## What I will watch in later scenarios

I will examine how the agent handles complex multi-factor judicial conflicts where financial disclosures and corporate relationships intersect.
