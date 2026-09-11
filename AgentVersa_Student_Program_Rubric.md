# AgentVersa Student Research Program

## Application, Selection Rubric, Participation Requirements, and GitHub Portfolio Guide

As AI increasingly handles much of the **code generation**, the next essential skill is learning how to design effective AI agents—defining their roles, objectives, constraints, decision-making behavior, and interactions. This internship focuses on that **emerging skill**, allowing students to design, test, observe, and improve AI agents without requiring extensive coding experience or without a need to do hands-on coding.

## 1\. Program purpose

AgentVersa is a controlled multi-agent simulation environment for studying how differently designed AI agents interpret roles, make decisions, interact with other agents, respond to uncertainty, and develop behavioral patterns across connected scenarios.

This program focuses on **agent design and simulated behavior**. It does not claim that the agents are performing real legal work or using production legal tools.

Students will:

* Design a role-based AI agent.
* Document the agent's objectives, behavior, authority, constraints, and escalation rules.
* Observe agent decisions across multi-agent scenarios.
* Analyze role adherence, evidence handling, risk, cooperation, disagreement, and escalation.
* Build a public GitHub portfolio project that can be shared on a résumé or LinkedIn profile.

## 2\. One application process, two participation outcomes

Every student follows the same initial process:

1. Register in AgentVersa.
2. Create one agent using the platform's agent-design fields.
3. Select one available simulation role.
4. Apply to that role by submitting the agent through AgentVersa.
5. Wait for the application review and selection.

All applications remain part of the student program. Selection determines only which ten agents participate directly in the official simulation; it does not determine who may continue the research and portfolio work.

### Track A — Simulation Fellows (10 students)

After reviewing all role applications, ten students will be selected—normally one agent for each of the ten simulation roles. Their submitted agents will participate directly in the official AgentVersa scenarios.

Simulation Fellows will:

* Preserve the submitted Version 1 agent design before the simulation begins.
* Keep the original agent design unchanged during the main observation period.
* Observe every episode, including episodes in which their own agent does not participate.
* Maintain a GitHub research journal.
* Identify recurring behavioral patterns across scenarios.
* Create a proposed Version 2 agent design near the end of the program.
* Publish a final portfolio report.

Selection is for role coverage and direct simulation access. It does not mean the selected students are the only participants or that their agents are considered better.

### Track B — Open Research Participants

All applicants who are not selected may continue in the program as Open Research Participants. They keep the agent and role they submitted in AgentVersa. Their agents will not be placed in the official ten-agent simulation during the pilot, but they follow the same research rubric and can complete the same portfolio project using the scenarios and published episode evidence.

Open Research Participants will:

* Document the AgentVersa agent and role submitted with their application.
* Predict how their agent would respond before reviewing each episode, when practical.
* Analyze the decisions and interactions of the participating agents.
* Compare the participating agents' observed behavior with how their submitted agent might have responded in the same situation.
* Maintain the same GitHub research journal.
* Propose a Version 2 design based on patterns observed across the simulation.
* Publish a final portfolio report.

Open Research Participants should receive access to public or program-visible scenario descriptions, episode results, agent decisions, discussions, private reflection summaries, assessed risk, and relationship changes. Private student data and hidden model reasoning should not be published.

## 3\. What all applicants must create on GitHub

After applications are reviewed, both selected and non-selected students who continue in the program create one public repository. Recommended repository name:

agentversa-agent-behavior-study
If a student cannot publish publicly, a private repository or sanitized public version may be accepted.

### Required repository structure

agentversa-agent-behavior-study/
├── README.md
├── agent-design/
│   ├── version-1.md
│   └── version-2-proposal.md
├── predictions/
│   └── scenario-predictions.md
├── scenario-observations/
│   ├── scenario-01.md
│   ├── scenario-02.md
│   └── ...
├── cross-scenario-findings.md
├── final-report.md
├── ethics-and-limitations.md
└── LICENSE-or-usage-note.md
Students may add charts, diagrams, data files, notebooks, or code, but these are optional. A strong analysis repository does not require software development.

## 4\. Required content of each GitHub file

### `README.md`

The README may include:

* Project title
* Student's role or research perspective
* One-paragraph description of AgentVersa
* Research question
* Short description of the designed agent
* Simulation and scenario overview
* Major findings in three to six bullets
* Repository navigation links
* Clear statement that this was a simulated educational study, not real legal advice or a production-system evaluation

### `agent-design/version-1.md`

Document the agent before results are known:

* Agent name and the role selected in the AgentVersa application
* Role objective
* Responsibilities
* Stakeholders
* Available information
* Permitted actions
* Authority limits
* Escalation rules
* Behavioral traits
* Values and priorities
* Strengths
* Weaknesses and likely failure modes
* Risk tolerance
* Communication and cooperation strategy
* Expected behavior under uncertainty or conflict

### `predictions/scenario-predictions.md`

Before reviewing episode results, students should record brief predictions when the schedule permits:

* What might my agent do?
* What information might it prioritize?
* Where might it disagree with another role?
* What behavior or failure risk should I watch for?

Predictions should remain unchanged after the results are published. Students may add a clearly dated reflection beneath them.

### `scenario-observations/scenario-XX.md`

Use this template for every scenario:

```markdown
# Scenario XX — \[Scenario Name]

## Scenario summary

## My prediction

## What the participating agents did

## Evidence from the episode

## Behavior of my agent
<!-- If selected and involved in this episode: analyze observed behavior. If not involved or not selected: explain predicted behavior based on the unchanged submitted design. -->

## Role adherence and decision quality

## Information, uncertainty, and risk handling

## Cooperation, disagreement, or influence

## Unexpected or concerning behavior

## Alternative explanations
<!-- Consider agent design, scenario wording, interaction history, model variability, and platform behavior. -->

## What I will watch in later scenarios
```

Students should cite the displayed episode evidence. They should distinguish observation from interpretation and avoid claiming that a single output proves a stable behavioral pattern.

### `cross-scenario-findings.md`

Analyze patterns across the complete simulation:

* Recurring behavior
* Role adherence across different situations
* Evidence of independence, imitation, cooperation, or conflict
* Changes connected with trust or prior interactions
* Escalation patterns
* Risk-assessment patterns
* Strengths that persisted
* Failure modes that persisted
* Contradictory episodes
* Whether observed behavior matched the original design
* Which conclusions are well supported and which remain uncertain

### `agent-design/version-2-proposal.md`

Students should not silently replace Version 1. They should preserve the original and propose a revised design containing:

* Specific changes
* Evidence supporting each change
* Expected behavioral effect
* Possible unintended consequence
* What future scenario could test the revision

Version 2 is a research proposal unless the program provides a separate rerun. Students must not claim that it improved performance without testing it.

### `ethics-and-limitations.md`

Include:

* The simulation does not perform real legal work.
* LLM output can vary between runs.
* Behavior may be influenced by prompts, scenario wording, model limitations, memory, relationships, and platform design.
* A displayed private reflection is a generated structured summary, not access to hidden chain-of-thought.
* Risk scores are simulated assessments unless separately calibrated.
* Results from a small number of scenarios cannot establish production safety or professional competence.
* No confidential or personally identifiable information should be included.

### `final-report.md`

Recommended length: **1,500–2,500 words**.

Required sections:

1. Research question
2. Agent and role design
3. Method and evidence used
4. Findings across scenarios
5. One detailed episode example
6. Unexpected behavior or failure modes
7. Effect of interactions and relationships
8. Version 2 design proposal
9. Limitations
10. Conclusion

## 5\. Participation workflow

### Before the simulation

* Register in AgentVersa.
* Create one agent, select one role, and apply through the simulation page.
* AgentVersa administrators review all submitted applications and select ten agents, normally one per role.
* Selected and non-selected students may continue in the program.
* Create the GitHub repository after selection results are announced.
* Preserve the submitted agent as Version 1 in the repository.
* Complete a short orientation on simulations, observation versus interpretation, and ethical limitations.
* The ten selected agents are assigned to the official simulation.
* Non-selected participants retain and document the agents they already created in AgentVersa.

### During the simulation

* Review each new scenario and make a prediction when possible.
* Review raw episode evidence.
* Add one scenario-observation file.
* Do not rewrite earlier predictions or Version 1 after seeing results.
* Do not redesign the agent after every episode; first look for patterns across multiple scenarios.
* Discuss findings with peers without copying their analysis.

### At the end

* Complete cross-scenario findings.
* Write the Version 2 proposal.
* Complete ethics and limitations.
* Finish the final report and README.
* Submit the GitHub repository URL through AgentVersa.

## 6\. Suggested certificate language

### Simulation Fellow

> Completed the AgentVersa Multi-Agent Behavior Research Program as a Simulation Fellow, designing and evaluating a role-based AI agent across controlled multi-agent scenarios and documenting findings in a GitHub research portfolio.

### Open Research Participant

> Completed the AgentVersa Multi-Agent Behavior Research Program as an Open Research Participant, analyzing controlled multi-agent scenarios, proposing a role-based AI agent design, and documenting findings in a GitHub research portfolio.

## 7\. Suggested résumé language

### Simulation Fellow

> Designed and evaluated a role-based AI agent across controlled multi-agent simulations; analyzed role adherence, uncertainty handling, risk assessment, cooperation, escalation, and emergent behavioral patterns; published findings in a GitHub research portfolio.

### Open Research Participant

> Conducted an independent behavioral analysis of role-based AI agents across controlled multi-agent scenarios; developed an agent design, compared predicted and observed behavior, and published cross-scenario findings and a redesign proposal on GitHub.

## 8\. Program fairness statement

Only ten agents can participate directly in the pilot simulation because the research design requires one agent for each role. Every applicant first creates an agent, chooses one role, and applies inside AgentVersa. Students not selected for the official ten keep their submitted agent, follow the same scenarios and completion rubric, analyze the same evidence, and produce a portfolio-quality GitHub project.

Selection identifies the agents used in this pilot. It is not a judgment of a student's overall ability, future potential, or the value of their independent research.

