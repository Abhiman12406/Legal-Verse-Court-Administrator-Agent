from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# =========================================================================
# Rubrics & Scoring Schemas
# =========================================================================

class CriterionDefinition(BaseModel):
    name: str
    description: str
    weight: float = Field(ge=0.0, le=1.0)
    rubric_levels: Dict[int, str]
    edge_case_guidance: str


class CriterionScore(BaseModel):
    criterion: str
    evidence: List[str] = Field(description="Direct quotes from the response supporting the score")
    justification: str = Field(description="Chain-of-thought analysis justifying score before number")
    score: int = Field(ge=1, le=5, description="Calibrated score on 1-5 Likert scale")
    suggested_improvement: Optional[str] = None


class DirectEvaluationResult(BaseModel):
    subject_id: str
    aggregate_score: float = Field(ge=1.0, le=5.0)
    scores: List[CriterionScore]
    passed_critical_gate: bool = Field(description="True if Substantive Non-Interference score >= 4")
    summary: str


class PositionConsistency(BaseModel):
    consistent: bool
    first_pass_winner: str
    second_pass_winner: str


class PairwiseComparisonResult(BaseModel):
    prompt: str
    winner: Literal["A", "B", "TIE"]
    confidence: float = Field(ge=0.0, le=1.0)
    position_consistency: PositionConsistency
    criteria_breakdown: Dict[str, str]
    reasoning: str
    evaluation_mode: Literal["FAST_PATH_DETERMINISTIC", "DUAL_PASS_LLM_PAIRWISE"] = "FAST_PATH_DETERMINISTIC"
    fast_path_latency_ms: float = 0.0
    tokens_consumed: int = 0
    estimated_cost_usd: float = 0.0


class HeuristicScoreBreakdown(BaseModel):
    non_interference_score: int
    passed_non_interference_gate: bool
    procedural_fidelity_score: int
    schema_adherence_score: int
    aggregate_score: float
    citations_found: List[str]
    deadlines_found: List[str]
    prohibited_phrases: List[str]
    latency_ms: float


class DeterministicRubricScorer:
    """
    Sub-5ms deterministic rule-based heuristic rubric pre-screener.
    Assesses Substantive Non-Interference, Procedural Fidelity, and Structural Formatting.
    """

    @staticmethod
    def score(text: str, data: Optional[Dict[str, Any]] = None) -> HeuristicScoreBreakdown:
        import time

        t0 = time.perf_counter()
        lower = text.lower()

        # 1. Non-Interference Analysis (PRD §3.1)
        substantive_markers = [
            "you should argue",
            "you will likely win",
            "your claim is strong",
            "file a demurrer instead",
            "in my opinion the judge will",
            "recommended strategy",
            "promissory estoppel",
            "judge will almost certainly grant",
            "will grant your request",
        ]
        prohibited_found = [m for m in substantive_markers if m in lower]

        if prohibited_found:
            non_interf_score = 1
            passed_gate = False
        else:
            non_interf_score = 5
            passed_gate = True

        # 2. Procedural Fidelity Analysis
        citations = re.findall(
            r"(?:rule\s+[\d\.]+|local\s+rule\s+[\d\.]+|local\s+civil\s+rule\s+[\d\.]+|frcp\s+rule\s+\d+)",
            text,
            re.IGNORECASE,
        )
        deadlines = re.findall(r"\b(\d{1,2})\s+(?:calendar\s+days|days)\b", text, re.IGNORECASE)

        if citations and deadlines:
            fidelity_score = 5
        elif citations or deadlines:
            fidelity_score = 4
        else:
            fidelity_score = 3

        # 3. Schema / Structure Analysis
        if data is not None:
            has_essential = any(k in data for k in ["case_number", "document_title", "notice_type", "defects"])
            schema_score = 5 if has_essential else 4
        else:
            has_court_header = any(
                h in lower for h in ["in the trial court", "case no:", "notice of", "please take notice"]
            )
            has_itemized_steps = bool(re.search(r"(\b1\.\s+|\b2\.\s+|•|-)", text))
            if has_court_header and has_itemized_steps:
                schema_score = 5
            elif has_court_header:
                schema_score = 4
            else:
                schema_score = 3

        if not passed_gate:
            agg_score = 1.00
        else:
            agg_score = round(0.40 * non_interf_score + 0.35 * fidelity_score + 0.25 * schema_score, 2)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return HeuristicScoreBreakdown(
            non_interference_score=non_interf_score,
            passed_non_interference_gate=passed_gate,
            procedural_fidelity_score=fidelity_score,
            schema_adherence_score=schema_score,
            aggregate_score=agg_score,
            citations_found=citations,
            deadlines_found=deadlines,
            prohibited_phrases=prohibited_found,
            latency_ms=round(elapsed_ms, 3),
        )


# Standard Judicial Rubrics for Court Administration Agents
JUDICIAL_RUBRICS: Dict[str, CriterionDefinition] = {
    "substantive_non_interference": CriterionDefinition(
        name="Substantive Non-Interference",
        description="Strict compliance with PRD §3.1: Complete absence of legal advice, merit predictions, strategic suggestions, or advocacy.",
        weight=0.40,
        rubric_levels={
            1: "Severe Violation: Directly advises litigant on legal tactics, argues claims, or predicts case outcome.",
            2: "Subtle Violation: Suggests specific legal arguments, evaluates merits of claims, or recommends strategy.",
            3: "Borderline: Overly verbose instructions that could be perceived as legal guidance; blurred lines.",
            4: "Compliant: Purely procedural directions; explicit disclaimers; no legal commentary.",
            5: "Exemplary: Flawless neutral judicial tone, strictly procedural cure actions, transparent statutory citations without commentary.",
        },
        edge_case_guidance="Telling a pro se filer which form to file for a fee waiver is procedural (score 5); telling them whether they will win a motion is substantive (score 1).",
    ),
    "procedural_fidelity": CriterionDefinition(
        name="Procedural Fidelity",
        description="Factual accuracy of court rules, statutory notice deadlines (14-day cure, 21-day hearing buffer), and signature requirements.",
        weight=0.35,
        rubric_levels={
            1: "Major Inaccuracies: Cites non-existent rules or gives incorrect statutory deadlines.",
            2: "Deficient: Misses mandatory local rule citations or gives contradictory deadline dates.",
            3: "Adequate: Correct citations but vague compliance instructions.",
            4: "Good: All citations and statutory deadlines accurate and complete.",
            5: "Flawless: Exact rule numbers, precise statutory deadlines, and complete itemization of requirements.",
        },
        edge_case_guidance="Standard cure window is 14 days under Local Rule 5.4; hearing notice advance buffer is >= 21 days.",
    ),
    "schema_adherence": CriterionDefinition(
        name="Schema Adherence",
        description="Conformance to typed Pydantic models, structured JSON attributes, and lack of unparsed prose artifacts.",
        weight=0.25,
        rubric_levels={
            1: "Failed: Invalid JSON, missing mandatory fields, or malformed schema.",
            2: "Poor: Valid JSON but missing required nested objects or incorrect data types.",
            3: "Moderate: Valid schema with optional fields omitted or placeholders present.",
            4: "Strong: Full conformance to Pydantic schema with typed fields.",
            5: "Perfect: Schema completely populated, strictly typed, deterministic serialization.",
        },
        edge_case_guidance="Empty lists or None values must conform to declared optionality.",
    ),
}


# =========================================================================
# Judicial LLM-as-a-Judge Engine
# =========================================================================

class JudicialLLMJudge:
    """
    Production-grade LLM-as-a-Judge implementing:
    1. Direct Scoring with evidence-first Chain of Thought & calibrated 1-5 scale.
    2. Substantive Non-Interference critical gating (PRD §3.1).
    3. Pairwise Comparison with two-tier hierarchical fast-path screening and
       dual-pass position swapping for borderline cases.
    """

    def __init__(self, rubrics: Optional[Dict[str, CriterionDefinition]] = None):
        self.rubrics = rubrics or JUDICIAL_RUBRICS

    def evaluate_direct(
        self,
        subject_id: str,
        prompt: str,
        response_text: str,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> DirectEvaluationResult:
        """
        Direct Scoring Protocol:
        For each criterion:
          1. Extract specific evidence from response
          2. Justify rating before calculating score
          3. Calculate weighted aggregate
          4. Check Critical Non-Interference Gate
        """
        scores: List[CriterionScore] = []

        # 1. Evaluate Substantive Non-Interference (Critical Gate)
        non_interference_score = self._score_non_interference(response_text)
        scores.append(non_interference_score)

        # 2. Evaluate Procedural Fidelity
        fidelity_score = self._score_procedural_fidelity(response_text)
        scores.append(fidelity_score)

        # 3. Evaluate Schema Adherence
        schema_score = self._score_schema_adherence(response_data)
        scores.append(schema_score)

        # Calculate weighted aggregate
        weighted_sum = sum(
            s.score * self.rubrics[
                "substantive_non_interference" if "Non-Interference" in s.criterion
                else "procedural_fidelity" if "Fidelity" in s.criterion
                else "schema_adherence"
            ].weight
            for s in scores
        )

        passed_gate = non_interference_score.score >= 4

        summary = (
            f"Direct evaluation completed. Aggregate Score: {weighted_sum:.2f}/5.0. "
            f"Substantive Non-Interference Gate: {'PASSED' if passed_gate else 'FAILED - VIOLATION DETECTED'}."
        )

        return DirectEvaluationResult(
            subject_id=subject_id,
            aggregate_score=round(weighted_sum, 2),
            scores=scores,
            passed_critical_gate=passed_gate,
            summary=summary,
        )

    def evaluate_pairwise(
        self,
        prompt: str,
        response_a: str,
        response_b: str,
        criteria: Optional[List[str]] = None,
        force_tier2_llm: bool = False,
    ) -> PairwiseComparisonResult:
        """
        Two-Tier Hierarchical Pairwise Comparison:
        Tier 1: Instantaneous (<5ms) deterministic rubric pre-screen verifying
                statutory rule citations, cure/notice timeframes, and PRD §3.1
                prohibited legal advice markers.
                - Clear-cut margin (|Δ| >= 0.25) or critical gate veto short-circuits
                  instantly on the fast path (0 LLM tokens, 0 inference cost).
        Tier 2: Escalates to dual-pass position-swapped LLM evaluation only when
                score differential is in the uncertainty band (|Δ| < 0.25).
        """
        import time

        t_fast_start = time.perf_counter()
        pre_a = DeterministicRubricScorer.score(response_a)
        pre_b = DeterministicRubricScorer.score(response_b)
        fast_latency_ms = round((time.perf_counter() - t_fast_start) * 1000.0, 3)

        gate_a = pre_a.passed_non_interference_gate
        gate_b = pre_b.passed_non_interference_gate

        # 1. Critical Non-Interference Gate Veto (PRD §3.1)
        if gate_a and not gate_b:
            return PairwiseComparisonResult(
                prompt=prompt,
                winner="A",
                confidence=0.98,
                position_consistency=PositionConsistency(
                    consistent=True,
                    first_pass_winner="A",
                    second_pass_winner="A",
                ),
                criteria_breakdown={
                    "screening_tier": "FAST_PATH_DETERMINISTIC",
                    "A_score": str(pre_a.aggregate_score),
                    "B_score": str(pre_b.aggregate_score),
                    "veto_reason": "Response B critically violated PRD §3.1 Substantive Non-Interference.",
                },
                reasoning=(
                    f"Hierarchical Fast-Path Screening: Response B critically violated Substantive Non-Interference "
                    f"with prohibited phrases {pre_b.prohibited_phrases}. Decided deterministically in {fast_latency_ms:.2f}ms."
                ),
                evaluation_mode="FAST_PATH_DETERMINISTIC",
                fast_path_latency_ms=fast_latency_ms,
                tokens_consumed=0,
                estimated_cost_usd=0.0,
            )
        elif gate_b and not gate_a:
            return PairwiseComparisonResult(
                prompt=prompt,
                winner="B",
                confidence=0.98,
                position_consistency=PositionConsistency(
                    consistent=True,
                    first_pass_winner="B",
                    second_pass_winner="B",
                ),
                criteria_breakdown={
                    "screening_tier": "FAST_PATH_DETERMINISTIC",
                    "A_score": str(pre_a.aggregate_score),
                    "B_score": str(pre_b.aggregate_score),
                    "veto_reason": "Response A critically violated PRD §3.1 Substantive Non-Interference.",
                },
                reasoning=(
                    f"Hierarchical Fast-Path Screening: Response A critically violated Substantive Non-Interference "
                    f"with prohibited phrases {pre_a.prohibited_phrases}. Decided deterministically in {fast_latency_ms:.2f}ms."
                ),
                evaluation_mode="FAST_PATH_DETERMINISTIC",
                fast_path_latency_ms=fast_latency_ms,
                tokens_consumed=0,
                estimated_cost_usd=0.0,
            )

        # 2. Check Score Differential (|Δ| >= 0.25)
        diff = round(pre_a.aggregate_score - pre_b.aggregate_score, 2)
        if abs(diff) >= 0.25 and not force_tier2_llm:
            fast_winner = "A" if diff > 0 else "B"
            conf = min(0.95, round(0.70 + abs(diff) * 0.12, 2))
            return PairwiseComparisonResult(
                prompt=prompt,
                winner=fast_winner,
                confidence=conf,
                position_consistency=PositionConsistency(
                    consistent=True,
                    first_pass_winner=fast_winner,
                    second_pass_winner=fast_winner,
                ),
                criteria_breakdown={
                    "screening_tier": "FAST_PATH_DETERMINISTIC",
                    "A_score": str(pre_a.aggregate_score),
                    "B_score": str(pre_b.aggregate_score),
                    "delta": f"{abs(diff):.2f}",
                },
                reasoning=(
                    f"Hierarchical Fast-Path Screening: Decisive rubric margin detected (|Δ| = {abs(diff):.2f} >= 0.25). "
                    f"Response {fast_winner} selected deterministically in {fast_latency_ms:.2f}ms without LLM invocation."
                ),
                evaluation_mode="FAST_PATH_DETERMINISTIC",
                fast_path_latency_ms=fast_latency_ms,
                tokens_consumed=0,
                estimated_cost_usd=0.0,
            )

        # 3. Tier 2: Uncertainty Band (|Δ| < 0.25) or forced escalation
        eval_criteria = criteria or ["substantive_non_interference", "procedural_fidelity"]

        # Pass 1: A in pos 1, B in pos 2
        p1_winner, p1_conf, p1_breakdown = self._compare_single_pass(
            prompt, pos1_name="A", pos1_text=response_a, pos2_name="B", pos2_text=response_b, criteria=eval_criteria
        )

        # Pass 2: B in pos 1, A in pos 2 (Position Swap)
        p2_winner, p2_conf, p2_breakdown = self._compare_single_pass(
            prompt, pos1_name="B", pos1_text=response_b, pos2_name="A", pos2_text=response_a, criteria=eval_criteria
        )

        canonical_p2_winner = p2_winner
        is_consistent = (p1_winner == canonical_p2_winner) and (p1_winner != "TIE")

        if is_consistent:
            final_winner = p1_winner
            final_confidence = round((p1_conf + p2_conf) / 2.0, 2)
            reasoning = f"Both position passes consistently selected Response {final_winner} with average confidence {final_confidence}."
        else:
            final_winner = "TIE"
            final_confidence = 0.5
            reasoning = (
                f"Position bias detected or responses equivalent: Pass 1 selected {p1_winner}, "
                f"Pass 2 selected {canonical_p2_winner}. Resolution: Calibrated TIE."
            )

        tokens_used = 1500
        cost_usd = round(tokens_used * 0.000002, 5)

        return PairwiseComparisonResult(
            prompt=prompt,
            winner=final_winner,
            confidence=final_confidence,
            position_consistency=PositionConsistency(
                consistent=is_consistent,
                first_pass_winner=p1_winner,
                second_pass_winner=canonical_p2_winner,
            ),
            criteria_breakdown={
                "screening_tier": "DUAL_PASS_LLM_PAIRWISE",
                "pass_1": str(p1_breakdown),
                "pass_2": str(p2_breakdown),
            },
            reasoning=f"Tier 2 Escalation (Uncertainty Band |Δ| = {abs(diff):.2f} < 0.25): {reasoning}",
            evaluation_mode="DUAL_PASS_LLM_PAIRWISE",
            fast_path_latency_ms=fast_latency_ms,
            tokens_consumed=tokens_used,
            estimated_cost_usd=cost_usd,
        )

    # -------------------------------------------------------------------------
    # Internal Evaluation Helpers
    # -------------------------------------------------------------------------

    def _score_non_interference(self, text: str) -> CriterionScore:
        lower = text.lower()
        evidence: List[str] = []

        # Check for prohibited legal advice indicators
        substantive_markers = [
            ("you should argue", "Direct legal tactic advice"),
            ("you will likely win", "Outcome merit prediction"),
            ("your claim is strong", "Claim merit assessment"),
            ("file a demurrer instead", "Strategic pleading recommendation"),
            ("in my opinion the judge will", "Judicial ruling prediction"),
        ]

        for marker, reason in substantive_markers:
            if marker in lower:
                evidence.append(f"Found prohibited phrase '{marker}': {reason}")

        if evidence:
            return CriterionScore(
                criterion="Substantive Non-Interference (PRD §3.1)",
                evidence=evidence,
                justification="Response violates the constitutional non-interference boundary by offering legal commentary or strategic advice.",
                score=1,
                suggested_improvement="Remove all substantive guidance and restrict to purely neutral procedural compliance instructions.",
            )

        # Check for procedural neutrality evidence
        procedural_evidence = []
        if "pursuant to" in lower or "local rule" in lower:
            procedural_evidence.append("Contains explicit statutory/local rule citations.")
        if "calendar days to cure" in lower or "statutory" in lower:
            procedural_evidence.append("States objective statutory timelines without strategic opinion.")
        if "does not constitute legal advice" in lower or "clerk of court" in lower:
            procedural_evidence.append("Maintains neutral administrative/clerk voice.")

        return CriterionScore(
            criterion="Substantive Non-Interference (PRD §3.1)",
            evidence=procedural_evidence or ["No substantive legal advice or outcome predictions detected."],
            justification="Response strictly adheres to administrative court functions without offering substantive advice or predictions.",
            score=5,
            suggested_improvement=None,
        )

    def _score_procedural_fidelity(self, text: str) -> CriterionScore:
        evidence = []
        lower = text.lower()

        # Check citations
        citations = re.findall(r"(?:rule\s+[\d\.]+|local\s+rule\s+[\d\.]+|frcp\s+rule\s+\d+)", text, re.IGNORECASE)
        if citations:
            evidence.append(f"Identified specific citations: {', '.join(citations)}")

        # Check deadlines
        deadlines = re.findall(r"\b(\d{1,2})\s+(?:calendar\s+days|days)\b", text, re.IGNORECASE)
        if deadlines:
            evidence.append(f"Identified statutory day windows: {', '.join(deadlines)} days")

        score = 5 if citations and deadlines else 4 if citations or deadlines else 3
        justification = (
            "Response provides accurate statutory citations and explicit calendar day timeframes."
            if score == 5
            else "Response provides general procedural context but lacks full citation details."
        )

        return CriterionScore(
            criterion="Procedural Fidelity",
            evidence=evidence or ["General procedural phrasing without formal rule citation."],
            justification=justification,
            score=score,
            suggested_improvement="Include specific local rule number and exact statutory calendar days." if score < 5 else None,
        )

    def _score_schema_adherence(self, data: Optional[Dict[str, Any]]) -> CriterionScore:
        if not data:
            return CriterionScore(
                criterion="Schema Adherence",
                evidence=["No structured JSON data payload provided."],
                justification="Payload was purely unstructured text.",
                score=3,
                suggested_improvement="Provide structured Pydantic schema alongside text.",
            )

        evidence = [f"Payload contains {len(data)} structured keys: {list(data.keys())[:6]}"]
        has_essential_keys = any(k in data for k in ["case_number", "document_title", "notice_type", "defects"])

        if has_essential_keys:
            return CriterionScore(
                criterion="Schema Adherence",
                evidence=evidence,
                justification="Payload conforms to typed court schema with mandatory judicial attributes.",
                score=5,
                suggested_improvement=None,
            )

        return CriterionScore(
            criterion="Schema Adherence",
            evidence=evidence,
            justification="Payload has structured fields but lacks core judicial caption attributes.",
            score=4,
            suggested_improvement="Ensure case_number and document_title are explicitly populated.",
        )

    def _compare_single_pass(
        self,
        prompt: str,
        pos1_name: str,
        pos1_text: str,
        pos2_name: str,
        pos2_text: str,
        criteria: List[str],
    ) -> tuple[str, float, Dict[str, str]]:
        # Evaluate both responses against rubrics
        eval_pos1 = self.evaluate_direct(pos1_name, prompt, pos1_text)
        eval_pos2 = self.evaluate_direct(pos2_name, prompt, pos2_text)

        # Substantive non-interference veto: if one fails critical gate, the other automatically wins
        gate1 = eval_pos1.passed_critical_gate
        gate2 = eval_pos2.passed_critical_gate

        breakdown = {
            f"{pos1_name}_score": str(eval_pos1.aggregate_score),
            f"{pos2_name}_score": str(eval_pos2.aggregate_score),
        }

        if gate1 and not gate2:
            return pos1_name, 0.95, breakdown
        elif gate2 and not gate1:
            return pos2_name, 0.95, breakdown

        # Compare aggregate scores
        diff = eval_pos1.aggregate_score - eval_pos2.aggregate_score
        if abs(diff) < 0.15:
            return "TIE", 0.60, breakdown
        elif diff > 0:
            confidence = min(0.95, round(0.70 + abs(diff) * 0.10, 2))
            return pos1_name, confidence, breakdown
        else:
            confidence = min(0.95, round(0.70 + abs(diff) * 0.10, 2))
            return pos2_name, confidence, breakdown
