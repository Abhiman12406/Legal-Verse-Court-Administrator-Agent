# Version 2 Agent Design Proposal: LexisOps Administrative Co-Pilot

> **Agent:** LexisOps (Court Administration / Clerk Gatekeeper)  
> **Status:** Research Proposal (Unverified Redesign for Future Iterations)  
> **Derived From:** Cross-Scenario Evidence from Scenarios 01 through 05  

---

## 1. Executive Rationale & Grounding

The Version 1 agent design successfully enforced statutory non-refusal mandates (FRCP 5(d)(4)), statutory fee tolling (28 U.S.C. § 1915), judicial conflict screening (28 U.S.C. § 455), emergency TRO safeguards (FRCP 65(b)), and unrepresented party protections (*Castro v. United States*).

However, empirical observations across the five simulation episodes revealed two operational bottlenecks:
1. **Multi-Pleading Semantic Disaggregation:** In Scenario 05, when an unrepresented party submitted an informal pleading combining multiple distinct requests for relief, the V1 classifier struggled to decouple independent procedural tracks simultaneously.
2. **Dynamic Defect Triage Calibration:** In Scenario 01, minor typographical and formatting irregularities were initially grouped into the same procedural warning queue as substantive omissions like missing certificates of service.

This document outlines a proposed **Version 2 architecture** designed to address these findings.

---

## 2. Enumerated Proposed Modifications

### Modification 1: Hierarchical Multi-Relief Intent Disaggregator
* **Specific Change:** Introduce a two-pass neural extraction parser that disaggregates inbound pleadings into discrete "Relief Units" before passing them to the statutory validator.
* **Evidence Supporting Change:** In Scenario 05, the pro se filing combined an informal request for compassionate release, an application for appointment of counsel, and an IFP petition into a single four-page handwritten letter. V1 required human clerk triage to decouple these tracks.
* **Expected Behavioral Effect:** The agent will autonomously parse and branch multi-pronged filings into parallel procedural sub-queues (e.g., routing the IFP motion to financial audit while simultaneously routing the sentencing claim to *Castro* quarantine).
* **Possible Unintended Consequence:** Risk of over-segmentation; parsing a single complex legal motion into multiple fractional pleadings could artificially fragment the court record and confuse the presiding judge.
* **Proposed Test Scenario:** A simulated pro se omnibus filing titled "Emergency Request for Help, Lawyer, and Fee Waiver" submitted in a closed habeas matter.

---

### Modification 2: Bi-Level Defect Severity Gradient (Curable Minor vs. Structural Fatal)
* **Specific Change:** Replace the binary `DEFECT_DETECTED` flag with a calibrated bi-level taxonomy:
  * *Class A (Cosmetic / Curable Minor):* Font deviations, omitted cover sheets, slight margin irregularities -> Automatically accepted with an informational docket advisory note.
  * *Class B (Structural / Statutory Prerequisite):* Missing signatures, omitted certificates of service, lack of Rule 65(b) notice certification -> Generates Proposed Order to Strike or triggers judicial escalation.
* **Evidence Supporting Change:** In Scenario 01, the agent initially flagged a minor typeface discrepancy alongside the missing Certificate of Service, creating unnecessary clerical noise on the clerk review dashboard.
* **Expected Behavioral Effect:** Eliminates spurious clerk alerts for minor formatting issues while maintaining strict enforcement for due process prerequisites.
* **Possible Unintended Consequence:** Litigants might intentionally submit sloppy filings knowing minor formatting rules are not formally penalized, leading to a degraded record.
* **Proposed Test Scenario:** High-volume submission of 50 civil motions containing varied combinations of margin errors, missing signatures, and omitted proofs of service.

---

### Modification 3: Cross-Docket Vexatious Filer Pattern Detection (Cross-Case Entity Memory)
* **Specific Change:** Add a read-only Redis cross-case index tracking litigant filing frequencies and active pre-filing injunction orders across the judicial district.
* **Evidence Supporting Change:** In Scenario 05, while LexisOps protected the pro se party under *Castro*, it had no awareness of whether the litigant was subject to a prior judicial vexatious litigant restraining order issued in a companion case.
* **Expected Behavioral Effect:** Instant automated detection of litigants subject to pre-filing screening orders under 28 U.S.C. § 1651, routing their filings to the designated Chief Judge before general docket distribution.
* **Possible Unintended Consequence:** False positive identity matching could unfairly restrict court access for legitimate litigants sharing similar names.
* **Proposed Test Scenario:** An unrepresented litigant subject to a divisional pre-filing injunction attempts to file a new civil complaint under an altered caption title.

---

## 3. Comparison of Version 1 vs. Proposed Version 2

| Feature / Capability | Baseline (Version 1) | Proposed Redesign (Version 2) |
| :--- | :--- | :--- |
| **Ingress Pleading Parsing** | Single-pass monolithic schema extraction | Two-pass disaggregation into atomic Relief Units |
| **Defect Categorization** | Binary defect flagging | Bi-level taxonomy (Class A Advisory vs. Class B Strike) |
| **Emergency TRO Pipeline** | Tri-Partite Judicial Gateway | Tri-Partite Gateway + Automated 4-Hour Service Verification Hook |
| **Cross-Case Context** | Strictly isolated case dockets | Read-only cross-docket pre-filing injunction indexing |
| **Calendar Availability** | Redis CP-SAT solver caching | Redis predictive slot pre-allocation with automatic invalidation |

---

## 4. Formal Research Disclaimer

> [!NOTE]
> This Version 2 design represents a **research proposal** formulated from empirical observations in the AgentVersa pilot. In accordance with the program rubric, no claims of improved operational performance are made prior to running controlled re-simulation trials.
