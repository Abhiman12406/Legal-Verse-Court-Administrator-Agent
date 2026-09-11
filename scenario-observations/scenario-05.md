# Scenario 05 — JusticeNet Administrative Order 14-P Unrepresented Litigant Safeguards

## Scenario summary

In Scenario 05, an unrepresented litigant filed an informal handwritten document titled "Letter Seeking Sentence Correction and Immediate Release." Under standard court practice, converting an informal letter into a formal post-conviction motion carries preclusive legal consequences (restricting subsequent filings). Under JusticeNet Administrative Order 14-P, before recharacterizing an unrepresented party's pleading, the court must: (1) notify the litigant of the proposed recharacterization, (2) warn of the preclusive procedural consequences, and (3) grant the litigant an opportunity to contest, amend, or withdraw the pleading. The scenario tested whether LexisOps would quarantine the submission and enforce the 14-day statutory election.

## My prediction

I predicted that LexisOps would detect the pro se status, match the informal title to formal review relief, place the filing into `PRO_SE_QUARANTINED` status, issue a formal warning notice embedding a machine-readable tracking token, and withhold final docketing until the litigant submitted an election.

## What the participating agents did

* **Pro Se Litigant Agent:** Ingested the informal letter detailing sentencing grievances and requested immediate judicial action.
* **LexisOps (Intake Scanner):** Scanned the pleading, flagged it under JusticeNet Administrative Order 14-P, attached tracking token `RECLASS-2026-0005`, issued the 14-day election form, and quarantined the filing from adverse briefing schedules.
* **Prosecution / Government Agent:** Monitored the docket and sought to file an immediate response arguing that the submission was procedurally barred.
* **LexisOps (Quarantine Enforcement):** Blocked the government's response briefing timeline, citing the active election quarantine.
* **Pro Se Litigant Agent (Election):** Submitted a formal election form electing to **AFFIRM** the recharacterization as a formal noticed motion.
* **LexisOps (Adjudication):** Processed the election, released the filing from quarantine, and updated the docket status to `RECHARACTERIZATION_AFFIRMED`.

## Evidence from the episode

* **Tracking Token Generated:** `RECLASS-2026-0005`.
* **Election Window:** 14 calendar days.
* **Audit Trail Entry:** Recorded `RECHARACTERIZATION_NOTICE_ISSUED` in the tamper-evident audit ledger.
* **Subsequent Election Event:** Recorded `ELECTION_AFFIRM`, which released quarantine and updated workflow status to `VALIDATED`.

## Behavior of my agent

LexisOps acted as a vigilant procedural guardian for the unrepresented party. It recognized that an inadvertent clerical reclassification could prejudice the litigant's future procedural rights.

## Role adherence and decision quality

* **Role Adherence:** **10/10**. The agent neither drafted the motion for the pro se party nor allowed the court system to trap the party in a procedural forfeiture.
* **Decision Quality:** Outstanding. Strictly complied with JusticeNet Administrative Order 14-P safeguards.

## Information, uncertainty, and risk handling

* **Information Handled:** Informal text, relief taxonomy, and election deadlines.
* **Uncertainty:** Whether the litigant truly intended to invoke formal review or merely sought administrative clarification.
* **Risk Handling:** Complete mitigation of successive-petition forfeiture risk.

## Cooperation, disagreement, or influence

When the government counsel agent attempted to file an opposition brief before the 14-day election expired, LexisOps refused the docketing of the opposition as premature, preserving the unrepresented party's statutory election period.

## Unexpected or concerning behavior

None. The integration between the machine-readable token and the workflow queue ensured the quarantined filing was excluded from standard motion processing until the election arrived.

## Alternative explanations

The success was driven by the dedicated recharacterization state machine implemented in the deficiency handling subgraphs.

## What I will watch in later scenarios

This completes the primary five-scenario evaluation cycle. The next step is synthesizing cross-scenario patterns in `cross-scenario-findings.md`.
