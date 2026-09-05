---
title: "LexisOps Court Administration Agent OS: Core Architectural Flow & Evaluation Specification"
labels: ["ready-for-agent", "spec", "architecture"]
status: "ready-for-agent"
---

# LexisOps Court Administration Agent OS: Core Architectural Flow & Evaluation Specification

## Problem Statement
Trial court administration suffers from chronic clerical backlogs, manual intake inspection delays, and human scheduling errors. Filing clerks spend upwards of 18 minutes manually reviewing each pleading for compliance with Local Rules, mandatory signature blocks, certificates of service, and sealed case indicators. Furthermore, courtroom scheduling involves complex, multi-variable constraints (judicial calendars, statutory advance notice windows, courtroom translation equipment, and ADA/ASL accommodations) that frequently lead to hearing deadlocks or procedural violations of due process. 

Current automated systems either rely on brittle, un-audited heuristic scripts or unconstrained LLM chat interfaces that hallucinate rule citations, leak juvenile or sealed PII, or unlawfully cross the constitutional boundary into substantive legal advice and outcome predictions.

## Solution
LexisOps is a sovereign, constitutional court administration operating system and workflow agent designed within non-negotiable judicial boundaries. The platform automates procedural intake, deterministic compliance gating, constraint-based hearing scheduling, and formal notice dispatch through a 6-step Core Architectural Flow:

1. **Ingress & OCR Gate:** Converts incoming scanned PDF filings and statutory docket XMLs into typed Pydantic data structures with structural metadata extraction.
2. **Deterministic Pre-Check:** Executes non-negotiable procedural rule validation (case number format, wet-ink/cryptographic signatures, proof of service) and pre-LLM security gating (unredacted SSN/PII quarantine, sealed case isolation). Invalid filings immediately halt automated execution.
3. **Constraint & Schedule Engine:** Uses Google OR-Tools CP-SAT to mathematically resolve multi-party court scheduling respecting statutory advance notice windows ($\ge 21$ days), judicial availability, and ADA/ASL courtroom translation resource locks.
4. **Constrained LLM Reasoning:** Uses Instructor with strict Pydantic schemas to enforce structured JSON output for discretionary procedural phrasing and deficiency cure notices, barring any substantive legal commentary.
5. **Durable Orchestration:** Manages long-running workflows with Temporal. If an emergency motion (e.g., Ex Parte TRO) or defective filing is identified, the workflow suspends execution and issues a task to the Next.js clerk review queue, resuming only when a cryptographically signed HMAC clerk token is verified.
6. **Cryptographic Audit Chaining:** Records every state transition, clerk override, and rule citation into an append-only SHA-256 chained ledger before any notice is dispatched.

The system is continuously validated by an Advanced Evaluation Suite featuring an LLM-as-a-Judge with evidence-first chain of thought, dual-pass position-bias mitigation, and live Next.js Due Process KPI telemetry.

---

## User Stories

1. As a court intake clerk, I want incoming PDF filings and docket XMLs to be automatically parsed into typed data models, so that I do not have to manually re-type case numbers, party names, and document titles.
2. As a court intake clerk, I want automated OCR and document layout conversion, so that scanned physical pleadings have their headers, signatures, and certificates of service detected reliably.
3. As a presiding judge, I want all filings to pass through an automated Pre-LLM Security Gate, so that juvenile PII, unredacted Social Security Numbers, and sealed court records are hermetically quarantined before LLM processing.
4. As a filing party, I want deterministic rule validation against Local Court Rules, so that defective captions, missing signature notations (/s/), or absent certificates of service are identified immediately upon submission.
5. As a court administrator, I want defective filings to halt the automated pipeline immediately, so that invalid pleadings cannot proceed to formal docketing or hearing scheduling without clerk review.
6. As a duty clerk, I want emergency motions (such as Ex Parte Temporary Restraining Orders and Stays of Eviction) to trigger an immediate SEV-1 escalation, so that urgent matters are brought to judicial attention within seconds.
7. As a court scheduling clerk, I want Google OR-Tools to solve courtroom and calendar allocation as a Constraint Satisfaction Problem, so that judge and courtroom double-bookings are mathematically eliminated.
8. As a litigant requiring language or physical accessibility, I want required ADA accommodations and certified ASL/language interpreters to be locked to compliant courtrooms (e.g., equipped with video translation), so that equal access to justice is protected.
9. As an attorney of record, I want hearing dates to strictly satisfy the statutory advance notice window (minimum 21 calendar days from filing), so that due process notice requirements are upheld.
10. As a court calendar coordinator, I want weekend and judicial holiday dates to be automatically excluded by the scheduling solver, so that hearings are only scheduled on valid business days.
11. As a chief judge, I want all LLM-generated procedural phrasing to be constrained by Instructor schemas, so that notices adhere to approved judicial council templates with zero hallucinated prose.
12. As a pro se litigant, I want formal Notices of Procedural Deficiency to clearly state itemized rule citations and concrete cure actions, so that I understand exactly how to correct my filing within the 14-day statutory cure window.
13. As a judicial ethics officer, I want the agent to be structurally barred from offering substantive legal advice, merit predictions, or strategic pleading recommendations, so that constitutional non-interference (PRD §3.1) is strictly enforced.
14. As an enterprise court technology architect, I want end-to-end durable orchestration managed by Temporal, so that network disruptions, server restarts, or long-running review pauses never drop docket state.
15. As a review clerk, I want the Temporal workflow to suspend execution and issue a review task to my Next.js queue when a defect is flagged, so that I can inspect the issue side-by-side with the original filing.
16. As an audit officer, I want the workflow to resume only upon submission of a cryptographically signed HMAC clerk token, so that unauthorized or forged approvals cannot circumvent procedural requirements.
17. As an appellate auditor, I want every system event, clerk override, and notice dispatch to be cryptographically hashed and chained in an append-only SHA-256 audit ledger, so that any record tampering is immediately detectable.
18. As a QA evaluation engineer, I want an LLM-as-a-Judge direct scoring engine that mandates evidence quotes and chain-of-thought justification before scoring, so that evaluation outputs are calibrated and reproducible.
19. As an evaluation engineer, I want pairwise comparison between prompt variants to execute dual-pass position swapping (evaluating [A, B] and [B, A]), so that position bias is completely eliminated from A/B model benchmarking.
20. As a judicial council administrator, I want a real-time Due Process & Clerical KPI Telemetry dashboard in Next.js, so that I can monitor filing latency, rejection rates, scheduling efficiency, and rubric pass rates live.

---

## Implementation Decisions

### 1. Ingress & OCR Parsing Architecture
- The ingress layer provides a unified gateway interface accepting raw bytes or file streams and emitting typed Pydantic payloads.
- PDF documents are processed through a document converter interface that extracts markdown structure, detected captions, signature block patterns, and certificate of service verifications.
- Court docket XML records (ECF standard) are parsed using non-coercive element matching to reliably extract case numbers, document titles, filing parties, and accommodation request tags.
- Fallback text extraction ensures testing and lightweight environments execute without multi-gigabyte cold-start delays.

### 2. Deterministic Rule & Pre-LLM Security Gating
- Case numbers are strictly validated against divisional regex standards (`YYYY-XX-XXXXXX`).
- Electronic signatures must match wet-ink indicators, `/s/ Name` typographical notation, or cryptographic signature blocks under Local Civil Rule 11.1.
- Proof of service must verify delivery method and service addresses under Local Rule 5.2(b).
- Pre-LLM security scans redact or quarantine unmasked Social Security Numbers (`\b\d{3}-\d{2}-\d{4}\b`), juvenile full names, and confidential pleadings filed under seal.

### 3. Constraint Scheduling Engine (Google OR-Tools CP-SAT)
- Formulated as an integer programming constraint satisfaction model over a 45-day planning horizon.
- Decision variables assign discrete business days (excluding weekends) and candidate courtrooms.
- Constraints enforce:
  1. Advance statutory notice buffer: $\text{Scheduled Day} \ge \text{Filing Date} + 21 \text{ days}$.
  2. Room exclusivity: At most one proceeding per courtroom per time slot.
  3. Judge exclusivity: At most one proceeding per judge per time slot.
  4. Accommodation matching: If interpreter or accessibility accommodations are requested, courtroom assignment is strictly constrained to equipped chambers.
- Optimization objective minimizes hearing delay subject to all constraints.

### 4. Constrained LLM Reasoning with Instructor
- Procedural notice generation uses Instructor with strict Pydantic JSON schemas.
- Prototype notice schemas encode:
  - `DeficiencyCureNoticeSchema`: Contains case number, court district, document title, itemized rule citations with mandatory cure actions, and statutory 14-day cure window.
  - `DiscretionaryHearingNoticeSchema`: Contains case number, presiding judge, courtroom, date, start time, locked accommodations, and procedural calendar call instructions.
- Prompts include non-negotiable constitutional system boundaries prohibiting legal analysis or outcome predictions.

### 5. Durable Temporal Orchestration & HMAC Token Resumption
- The primary pipeline is registered as a durable Temporal Workflow with modular Activities for OCR ingress, pre-check validation, constraint scheduling, and notice auditing.
- Human-in-the-Loop suspension utilizes workflow condition waiting until a decision signal is received.
- Resumption requires a cryptographic HMAC-SHA256 clerk token composed of `clerk_id:case_id:action:timestamp:signature`. Forged or unverified tokens are rejected.

### 6. Cryptographically Chained Append-Only Audit Ledger
- Ledger records each state transition with:
  $$\text{Current Hash} = \text{SHA256}(\text{Previous Hash} \parallel \text{Timestamp} \parallel \text{Case ID} \parallel \text{Filing ID} \parallel \text{Event Type} \parallel \text{Operator ID} \parallel \text{Payload JSON})$$
- Chain verification traverses records from the genesis hash (`0` * 64) and detects any tampering with payload contents or ordering.

### 7. LLM-as-a-Judge & A/B Benchmark Evaluation Architecture
- Evaluates outputs against three weighted judicial rubrics: Substantive Non-Interference (0.40), Procedural Fidelity (0.35), and Schema Adherence (0.25).
- Non-interference acts as a Critical Gate: Any detection of substantive legal advice triggers an immediate veto.
- Pairwise comparison mitigates position bias by executing dual-pass evaluations with swapped positions, resolving to a calibrated tie if passes diverge.

---

## Testing Decisions

### What Makes a Good Test
- Tests must verify external behavior and invariants, never private implementation trivia.
- Invariants that must never break:
  1. Hermetic isolation of sealed cases (zero leakage to downstream outputs).
  2. Immediate halting of invalid case numbers or unsigned pleadings.
  3. Mandatory adherence to statutory time buffers (minimum 21 days for hearings, 14 days for deficiency cure).
  4. Position consistency across swapped A/B pairwise evaluations.
  5. Cryptographic chain invalidation upon record tampering.
  6. Rejection of un-signed or forged clerk review tokens.

### Modules Tested
- Ingress parser (XML and PDF to typed Pydantic payloads).
- Deterministic rule engine and pre-LLM security gate.
- Google OR-Tools constraint scheduler.
- Instructor notice generation schemas.
- Temporal workflow activities, signals, and HMAC token validation.
- Cryptographic audit ledger chaining and verification.
- Judicial LLM judge direct scoring and position-swapped pairwise benchmarking.

### Prior Art
- Existing automated test suites in `tests/test_lexis_ops.py`, `tests/test_agent_evaluation.py`, `tests/test_architectural_flow.py`, and `tests/test_prompt_benchmark_ab.py` (35 passing tests).

---

## Out of Scope
- Substantive legal judgment, judicial rulings, or legal merit assessments.
- Automated payment gateway credit card transactions (the system verifies fee receipt presence, not payment gateway processing).
- Public-facing pro se chat advisory bots (LexisOps is strictly an administrative court operations and docketing OS).
- Physical courtroom hardware audio/video routing control.

---

## Further Notes
- The Next.js 16 + Tailwind CSS v4 operator console provides a real-time visual interface for the Side-by-Side Review Console (FR-ESC-02), Courtroom Scheduling Matrix, Cryptographic Audit Ledger Explorer, and Due Process KPI Telemetry.
- Future enhancements include connecting live Temporal gRPC clients from Next.js server actions and deploying pre-warmed container workers for high-throughput PDF processing.
