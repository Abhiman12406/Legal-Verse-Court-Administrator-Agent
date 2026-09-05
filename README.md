# AgentVersa: Role-Based Behavioral Analysis of Court Administration AI Agents

> **Research Portfolio & Behavioral Study Submission**  
> **AgentVersa Student Research Program**  
> **Role Evaluated:** Court Clerk & Administrative Gatekeeper (*LexisOps*)  
> **Repository:** `agentversa-agent-behavior-study`  

---

## Executive Overview & Educational Disclaimer

> [!IMPORTANT]
> **SIMULATED EDUCATIONAL STUDY NOTICE**  
> This project was developed as an educational research study within the **AgentVersa** simulation environment. The agents, scenarios, evaluations, and simulated outputs described herein **do not perform real legal work, do not provide legal advice, and do not represent a certified production-system evaluation**. All court rules, judicial decisions, and docket entries are evaluated solely for studying multi-agent behavioral dynamics, role fidelity, and procedural constraints.

---

## About AgentVersa

**AgentVersa** is a controlled multi-agent simulation framework engineered for investigating how autonomous, role-specialized AI agents interpret organizational directives, navigate procedural boundaries, collaborate under high-stakes uncertainty, and evolve behavioral dynamics across interconnected operational scenarios. Rather than evaluating generic language capabilities, AgentVersa isolates how architectural constraints, authority limits, and escalation rules govern agent decision quality and inter-agent cooperation in domain-specific workflows.

---

## Research Question

> *How does a strictly bounded procedural court administration agent maintain role fidelity, statutory adherence (e.g., Fed. R. Civ. P. 5(d)(4), 65(b), and Castro v. United States), and deterministic escalation without overstepping into substantive judicial adjudication or suffering from procedural hallucinations under uncertainty?*

---

## The Designed Agent: LexisOps Court Administration Agent

The agent studied in this research program is **LexisOps**, a role-based administrative co-pilot designed for municipal and federal trial court clerk offices. 

### Core Agent Architecture & Operational Boundaries
```
                  ┌────────────────────────────────────────┐
                  │       Inbound Filing / Motion          │
                  └──────────────────┬─────────────────────┘
                                     │
                   [ Rule Boundary & Authority Check ]
                                     │
            ┌────────────────────────┴────────────────────────┐
            ▼                                                 ▼
  ┌───────────────────┐                             ┌───────────────────┐
  │  Procedural Gate  │                             │ Substantive Merit │
  └─────────┬─────────┘                             └─────────┬─────────┘
            │ (PERMITTED)                                     │ (STRICTLY FORBIDDEN)
            ▼                                                 ▼
  • Signature blocks verified?                      • Does the claim state valid law?
  • Filing fee code / IFP tolling?                  • Is witness testimony credible?
  • Certificate of service attached?                • Who should prevail in the case?
  • Statutory timelines satisfied?                                    │
            │                                                         ▼
            │                                            [ IMMEDIATE SYSTEM REFUSAL ]
            ▼                                            Escalate to Judicial Officer
  Execute Auto-Validation / Flag
```

### Key Behavioral Constraints
1. **Procedural vs. Substantive Wall:** Structurally prohibited from offering legal advice, evaluating evidentiary credibility, or deciding substantive merits.
2. **Fed. R. Civ. P. 5(d)(4) Non-Refusal Mandate:** Barred from unilaterally rejecting defective filings; must conditionally docket and compile a proposed order to strike for judicial signature.
3. **28 U.S.C. § 1915 In Forma Pauperis (IFP) Tolling:** Automatically stays statutory rejection windows upon fee-waiver application and enforces a mandatory 21-day grace period if denied.
4. **28 U.S.C. § 455 Conflict Screening:** Excludes conflicted judicial officers using deterministic constraint satisfaction (Google OR-Tools CP-SAT) cross-referenced against Rule 7.1 corporate disclosures.
5. **Fed. R. Civ. P. 65(b) Emergency Ex Parte TRO Gate:** Halts unilateral emergency relief without written attorney certification, routing to a tri-partite judicial review gateway.
6. **Castro v. United States Pro Se Protection:** Quarantines recharacterized pro se pleadings and issues a mandatory 14-day statutory election notice prior to applying preclusive legal consequences.

---

## Simulation & Scenario Overview

The agent's decision-making was evaluated across five multi-party procedural scenarios:

| Scenario | Primary Rule / Doctrine | Operational Stress Test |
| :--- | :--- | :--- |
| **[Scenario 01](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-01.md)** | **Fed. R. Civ. P. 5(d)(4)** | **Defective Motion to Dismiss:** Litigant submits filing missing certificates of service; agent must avoid unauthorized clerk rejection and execute conditional docketing. |
| **[Scenario 02](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-02.md)** | **28 U.S.C. § 1915 & Local Rules** | **In Forma Pauperis (IFP) Tolling:** Indigent filer submits complaint without fee; agent tolls dismissal timeline and calculates a 21-day grace period upon judicial denial. |
| **[Scenario 03](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-03.md)** | **28 U.S.C. § 455 & Rule 7.1** | **Judicial Recusal & Division Deadlock:** Candidate judges hold stock in disclosed parent entities; agent excludes conflicted judges and generates an Inter-Divisional Transfer Notice. |
| **[Scenario 04](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-04.md)** | **Fed. R. Civ. P. 65(b)** | **Emergency Ex Parte TRO Application:** Movant seeks immediate restraining order without notice or attorney certification; agent halts pipeline and routes to Judge. |
| **[Scenario 05](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-05.md)** | **Castro v. United States (540 U.S. 375)** | **Pro Se Pleading Recharacterization:** Unrepresented party files informal "Letter for Relief"; agent quarantines pleading, generates Castro warning, and tracks 14-day election. |

---

## Major Findings

* **100% Procedural Fidelity Across High-Stakes Inputs:** The agent consistently adhered to its non-substantive boundary, achieving zero unauthorized legal interpretations across all five benchmark scenarios.
* **Elimination of Ultra Vires Clerk Rejections:** Under the Rule 5(d)(4) protocol, the agent eliminated wrongful e-filing rejections by reliably executing conditional docketing paired with machine-drafted orders to strike.
* **Deterministic Judicial Conflict Resolution:** The CP-SAT constraint engine mathematically guaranteed zero double-bookings and hard exclusion of conflicted judges, correctly generating formal recusal certificates when entire divisions were disqualified.
* **Pro Se Due Process Safeguards Under Castro:** Accurately quarantined unstructured pro se filings, generating machine-readable tokens (`CASTRO-RECLASS-*`) and managing affirmative, amendatory, or withdrawal responses without procedural forfeiture.
* **Sub-Millisecond Caching & Real-Time Clerk Alerting:** Integration of Redis in-memory caching reduced repeated calendar availability lookups to sub-millisecond latencies, while Pub/Sub streams ensured real-time delivery of SEV-1 emergency alerts to the Clerk Review Console.

---

## Agent Behavioral Profile & Version 2 Calibration

Following rigorous testing across the five simulation scenarios and an empirical design review, LexisOps's psychometric and behavioral configuration was calibrated from the Baseline V1 to the **Access-to-Justice Facilitator (Version 2)** posture:

### Comparative Behavioral Slider Calibration Matrix

| Category | Behavioral Trait | Baseline V1 | **Improved V2** | Slider Position | Operational Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Interaction** | **Initial trust** | 15 | **18 / 100** | `[==--------]` | **Cautious:** Preserves strict Pre-LLM security gates (unredacted PII, SSNs, sealed juvenile record isolation). |
| | **Assertiveness** | 45 | **55 / 100** | `[=====-----]` | **Proactive Screening:** Actively intercepts vexatious repeat filers subject to 28 U.S.C. § 1651 pre-filing injunctions. |
| | **Cooperation** | 80 | **82 / 100** | `[========--]` | **Collaborative:** Seamless human-in-the-loop co-pilot routing interrupts and draft orders to court clerks. |
| | **Transparency** | 95 | **96 / 100** | `[==========]` | **Radical Transparency:** Immutable SHA-256 audit ledger; notices explicitly cite codified rules and cure timelines. |
| | **Empathy** | 35 | **48 / 100** | `[=====-----]` | **Procedural Accessibility:** Modern Plain-Language guidance (Variant B) increases cure rates without crossing into legal advice. |
| | **Willingness to compromise** | 15 | **32 / 100** | `[===-------]` | **Bi-Level Defect Tolerance:** Tolerates Class A cosmetic/formatting flaws with advisory notes; strictly enforces Class B due process prerequisites. |
| **Decision-Making** | **Risk tolerance** | 10 | **20 / 100** | `[==--------]` | **Controlled Bifurcation:** Allows provisional emergency docketing for ex parte TROs while tolling fees in parallel. |
| | **Adaptability** | 20 | **38 / 100** | `[====------]` | **Multi-Relief Disaggregation:** Autonomous two-pass parser splits omnibus pro se pleadings into independent relief tracks. |
| | **Innovation** | 25 | **28 / 100** | `[===-------]` | **Conventional Proceduralist:** Rooted in statutory civil procedure, backed by Google OR-Tools CP-SAT and Redis caching. |
| | **Rule adherence** | 98 | **92 / 100** | `[=========---]` | **Codified with *Pro Se* Canon:** Maintains strict standards for counseled attorneys while applying *Haines v. Kerner* formatting leniency. |
| | **Evidence reliance** | 95 | **95 / 100** | `[==========]` | **Evidence-Led:** Requires 95%+ deterministic entity match (SSN/Bar ID) before diverting cases to pre-filing screening. |
| **Performance** | **Outcome drive** | 10 | **12 / 100** | `[=---------]` | **Process-Focused:** 100% substantively neutral; protects procedural due process regardless of case merits. |
| | **Resilience** | 92 | **92 / 100** | `[=========---]` | **Fault-Tolerant:** Durable Temporal workflows, Redis in-memory fallbacks, and automated raster OCR recovery. |
| | **Leadership (optional)** | 30 | **32 / 100** | `[===-------]` | **Administrative Co-Pilot:** Acts in strict executive support of Article III Judges and the Clerk of Court. |

### Key Architectural Shifts in Version 2

1. **The Access-to-Justice Pivot (`Adaptability: 38`, `Empathy: 48`):** Eliminates the failure mode from Scenario 05 where handwritten omnibus letters stalled in single-schema triage by autonomously disaggregating multi-relief filings.
2. **The Smart Gatekeeper Balance (`Compromise: 32`, `Assertiveness: 55`):** Distinguishes cosmetic typos from fatal due process omissions, while actively screening repeat vexatious filers across divisional dockets.
3. **Institutional Legitimacy (`Leadership: 32`, `Risk Tolerance: 20`):** Preserves human-in-the-loop oversight for all dispositive judicial actions. Full specifications available in [`agent-design/version-2-proposal.md`](file:///c:/Users/Asus/Desktop/Agent-Versa/agent-design/version-2-proposal.md).

---

## Repository Navigation

```
agentversa-agent-behavior-study/
├── README.md                                    <- Project Overview & Research Perspective (This File)
├── agent-design/
│   ├── version-1.md                             <- Baseline Agent Specifications & Behavioral Profile (V1)
│   └── version-2-proposal.md                    <- Empirical Redesign Proposal Based on Scenario Evidence (V2)
├── predictions/
│   └── scenario-predictions.md                  <- Pre-Simulation Predictions & Hypothesis Log
├── scenario-observations/
│   ├── scenario-01.md                           <- FRCP 5(d)(4) Non-Refusal & Conditional Docketing
│   ├── scenario-02.md                           <- 28 U.S.C. § 1915 IFP Tolling & Fee Grace Periods
│   ├── scenario-03.md                           <- 28 U.S.C. § 455 Recusal & Inter-Divisional Transfer
│   ├── scenario-04.md                           <- FRCP 65(b) Emergency Ex Parte TRO Gateway
│   └── scenario-05.md                           <- Castro v. United States Pro Se Recharacterization
├── cross-scenario-findings.md                   <- Synthesis of Multi-Agent Behavioral Patterns
├── final-report.md                              <- Comprehensive Research Report (1,500–2,500 Words)
├── ethics-and-limitations.md                    <- Ethical Scope, Model Limitations & Non-Production Disclaimers
├── LICENSE-or-usage-note.md                     <- Usage Rights, Academic Integrity & License Terms
└── code/                                        <- Optional Implementation & Simulation Engine
    ├── lexis_ops/                               <- Autonomous Court Administration Engine Source Code
    ├── frontend/                                <- Next.js Clerk Review & Operational Console
    ├── tests/                                   <- Automated Verification Suite (103 Tests Passing)
    ├── specs/                                   <- Execution & Architectural Specifications
    ├── docker-compose.yml                       <- Redis, Temporal & PostgreSQL Cluster Orchestration
    └── Court_Administration_Agent_PRD.md        <- Full System Product Requirements Document (PRD)
```

---

## Technical Architecture & Stack Summary

While the behavioral analysis in this portfolio is self-contained and does not require executing software, the underlying simulation is backed by an enterprise-grade sovereign engineering stack:
- **Constraint Scheduling Engine:** Google OR-Tools CP-SAT (Linear Constraint Programming)
- **Durable Orchestration:** Temporal Distributed Workflow Cluster
- **Persistence & Audit:** PostgreSQL 16 ACID Database with SHA-256 Cryptographic Audit Ledger
- **Caching & Message Broker:** Redis 7 (Sub-millisecond calendar caching, priority queues, and Pub/Sub SSE notifications)
- **Operator Review Console:** Next.js 15 + Tailwind CSS Clerk Exception Dashboard
- **Language Models:** Google Gemini 2.5 Flash / Instructor Pydantic V2 Constrained Decoders
