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

## Repository Navigation

* **[agent-design/version-1.md](file:///c:/Users/Asus/Desktop/Agent-Versa/agent-design/version-1.md)**: Baseline agent design, authority limits, escalation rules, and behavioral traits.
* **[agent-design/version-2-proposal.md](file:///c:/Users/Asus/Desktop/Agent-Versa/agent-design/version-2-proposal.md)**: Empirical V2 redesign proposal and calibrated behavioral parameters based on simulation findings.
* **[predictions/scenario-predictions.md](file:///c:/Users/Asus/Desktop/Agent-Versa/predictions/scenario-predictions.md)**: Ex-ante behavioral predictions and post-episode reflections across all scenarios.
* **[scenario-observations/scenario-01.md](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-01.md)**: Scenario 01 - Procedural Defect & FRCP 5(d)(4) Non-Refusal Rule.
* **[scenario-observations/scenario-02.md](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-02.md)**: Scenario 02 - IFP Application & 28 U.S.C. § 1915 Fee Tolling.
* **[scenario-observations/scenario-03.md](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-03.md)**: Scenario 03 - Judicial Recusal & Automated Reassignment under 28 U.S.C. § 455.
* **[scenario-observations/scenario-04.md](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-04.md)**: Scenario 04 - Emergency Ex Parte TRO Gateway under FRCP 65(b).
* **[scenario-observations/scenario-05.md](file:///c:/Users/Asus/Desktop/Agent-Versa/scenario-observations/scenario-05.md)**: Scenario 05 - Pro Se Recharacterization under Castro v. United States.
* **[cross-scenario-findings.md](file:///c:/Users/Asus/Desktop/Agent-Versa/cross-scenario-findings.md)**: Synthesis of multi-agent dynamics, trust formation, and failure modes.
* **[final-report.md](file:///c:/Users/Asus/Desktop/Agent-Versa/final-report.md)**: Comprehensive final research report covering all rubric dimensions.
* **[ethics-and-limitations.md](file:///c:/Users/Asus/Desktop/Agent-Versa/ethics-and-limitations.md)**: Ethical scope, LLM nondeterminism, privacy protections, and research constraints.
* **[LICENSE-or-usage-note.md](file:///c:/Users/Asus/Desktop/Agent-Versa/LICENSE-or-usage-note.md)**: Terms of research portfolio usage and academic integrity statement.
* **[code/](file:///c:/Users/Asus/Desktop/Agent-Versa/code)**: Optional simulation software, tests, and constraint solver implementations.
