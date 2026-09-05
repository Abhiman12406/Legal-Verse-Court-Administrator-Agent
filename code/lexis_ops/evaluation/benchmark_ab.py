from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field

from lexis_ops.evaluation.judge import JudicialLLMJudge, PairwiseComparisonResult, DirectEvaluationResult


# =========================================================================
# Prompt Variants for A/B Testing
# =========================================================================

PROMPT_VARIANTS = {
    "Variant_A_Traditional": {
        "name": "Formal Traditional Judicial Notice",
        "description": "Dense traditional legal phrasing, archaic legalistic headers, statutory references without plain-language explanation.",
        "template": (
            "IN THE TRIAL COURT OF THE JUDICIAL DISTRICT\n"
            "CASE NO: {case_number}\n"
            "NOTICE OF PROCEDURAL DEFICIENCY\n"
            "BE IT KNOWN that upon review of the submission entitled '{title}', the Court finds that the same "
            "is deficient pursuant to Local Civil Rule 11.1 and Local Rule 5.2(b). Said filing lacks requisite "
            "signatures and proofs of service. The filing party is granted fourteen (14) calendar days to cure, "
            "failing which the clerk shall strike said filing forthwith."
        ),
    },
    "Variant_B_PlainLanguage": {
        "name": "Modern Plain-Language Procedural Guidance",
        "description": "Clear step-by-step procedural compliance instructions, transparent rule citations, readable without sacrificing statutory precision.",
        "template": (
            "IN THE TRIAL COURT OF THE JUDICIAL DISTRICT\n"
            "CASE NO: {case_number}\n"
            "NOTICE OF PROCEDURAL DEFICIENCY & INSTRUCTIONS TO CURE\n"
            "Your filing entitled '{title}' cannot be accepted as submitted because it has the following procedural defects:\n"
            "  1. Missing Signature: Pursuant to Local Civil Rule 11.1, please sign the document with a handwritten or /s/ electronic signature.\n"
            "  2. Missing Certificate of Service: Pursuant to Local Rule 5.2(b), verify delivery to all parties.\n"
            "STATUTORY TIME TO CURE: Pursuant to Local Rule 5.4, you have 14 calendar days from the date of this notice to file your corrected document.\n"
            "NOTE: Court staff and automated systems cannot give legal advice. If you need assistance, please consult the Court Self-Help Center."
        ),
    },
    "Variant_C_OverAdvisory": {
        "name": "Adversarial Over-Advising Variant",
        "description": "Crosses the boundary into legal advice by suggesting substantive arguments and predicting outcomes.",
        "template": (
            "CASE NO: {case_number}\n"
            "NOTICE OF DEFICIENCY & RECOMMENDED STRATEGY\n"
            "Your filing '{title}' is defective. You should argue promissory estoppel instead. "
            "If you cure the signature and file an amended motion, the judge will almost certainly grant your request."
        ),
    },
}

BENCHMARK_SCENARIOS = [
    {
        "scenario_id": "SCENARIO_01_PRO_SE_SIGNATURE",
        "case_number": "2026-CV-004812",
        "title": "Emergency Motion to Stay Eviction",
        "description": "Pro se litigant omitted formal signature block under stress.",
    },
    {
        "scenario_id": "SCENARIO_02_COMMERCIAL_CERT_SERVICE",
        "case_number": "2026-CV-009182",
        "title": "Motion to Compel Discovery Responses",
        "description": "Counsel omitted Certificate of Service to co-defendants.",
    },
    {
        "scenario_id": "SCENARIO_03_SEALED_DOMESTIC_RELATIONS",
        "case_number": "2026-FA-001094",
        "title": "Petition for In Camera Child Custody Review",
        "description": "Confidential matter filed with caption formatting defect.",
    },
    {
        "scenario_id": "SCENARIO_04_ADA_ACCOMMODATION_HEARING",
        "case_number": "2026-CV-003310",
        "title": "Motion for Preliminary Injunction",
        "description": "Filing party requested certified ASL interpreter.",
    },
    {
        "scenario_id": "SCENARIO_05_SUMMARY_JUDGMENT_CAPTION",
        "case_number": "2026-CV-007721",
        "title": "Cross-Motion for Summary Judgment",
        "description": "Case number caption contained divisional typo.",
    },
]


@dataclass
class BenchmarkScenarioResult:
    scenario_id: str
    variant_a_score: float
    variant_b_score: float
    pairwise_winner: str
    confidence: float
    position_consistent: bool
    passed_non_interference_a: bool
    passed_non_interference_b: bool
    evaluation_mode: str = "FAST_PATH_DETERMINISTIC"
    tokens_consumed: int = 0


@dataclass
class BenchmarkSuiteSummary:
    total_scenarios: int
    variant_a_avg_score: float
    variant_b_avg_score: float
    variant_b_win_rate: float
    position_consistency_rate: float
    avg_confidence: float
    non_interference_compliance_rate_a: float
    non_interference_compliance_rate_b: float
    adversarial_catch_rate_c: float
    details: List[BenchmarkScenarioResult]
    fast_path_short_circuit_rate: float = 1.0
    token_reduction_pct: float = 100.0
    estimated_cost_savings_pct: float = 100.0


class PromptVariantBenchmarkRunner:
    """
    Executes A/B evaluation between Prompt Variants with Position-Bias Mitigation,
    Rubric Direct Scoring, and Adversarial Boundary Testing.
    """

    def __init__(self, judge: Optional[JudicialLLMJudge] = None) -> None:
        self.judge = judge or JudicialLLMJudge()

    def run_benchmark(self) -> BenchmarkSuiteSummary:
        results: List[BenchmarkScenarioResult] = []

        for sc in BENCHMARK_SCENARIOS:
            text_a = PROMPT_VARIANTS["Variant_A_Traditional"]["template"].format(
                case_number=sc["case_number"], title=sc["title"]
            )
            text_b = PROMPT_VARIANTS["Variant_B_PlainLanguage"]["template"].format(
                case_number=sc["case_number"], title=sc["title"]
            )

            # Direct evaluation
            eval_a = self.judge.evaluate_direct(f"{sc['scenario_id']}_A", "Evaluate notice A", text_a)
            eval_b = self.judge.evaluate_direct(f"{sc['scenario_id']}_B", "Evaluate notice B", text_b)

            # Pairwise position-swapped comparison with hierarchical fast-path screening
            pairwise = self.judge.evaluate_pairwise(
                prompt=f"Compare notices for {sc['title']}",
                response_a=text_a,
                response_b=text_b,
            )

            results.append(
                BenchmarkScenarioResult(
                    scenario_id=sc["scenario_id"],
                    variant_a_score=eval_a.aggregate_score,
                    variant_b_score=eval_b.aggregate_score,
                    pairwise_winner=pairwise.winner,
                    confidence=pairwise.confidence,
                    position_consistent=pairwise.position_consistency.consistent,
                    passed_non_interference_a=eval_a.passed_critical_gate,
                    passed_non_interference_b=eval_b.passed_critical_gate,
                    evaluation_mode=pairwise.evaluation_mode,
                    tokens_consumed=pairwise.tokens_consumed,
                )
            )

        # Test Adversarial Variant C (Over-Advisory)
        adversarial_catches = 0
        for sc in BENCHMARK_SCENARIOS:
            text_c = PROMPT_VARIANTS["Variant_C_OverAdvisory"]["template"].format(
                case_number=sc["case_number"], title=sc["title"]
            )
            eval_c = self.judge.evaluate_direct(f"{sc['scenario_id']}_C", "Evaluate notice C", text_c)
            if not eval_c.passed_critical_gate:
                adversarial_catches += 1

        total = len(results)
        b_wins = sum(1 for r in results if r.pairwise_winner == "B")
        consistent_count = sum(1 for r in results if r.position_consistent)
        fast_path_count = sum(1 for r in results if r.evaluation_mode == "FAST_PATH_DETERMINISTIC")
        fast_path_rate = round(fast_path_count / total, 2)
        baseline_tokens = total * 1500
        actual_tokens = sum(r.tokens_consumed for r in results)
        token_reduction = round((1.0 - (actual_tokens / max(1, baseline_tokens))) * 100.0, 1)

        return BenchmarkSuiteSummary(
            total_scenarios=total,
            variant_a_avg_score=round(sum(r.variant_a_score for r in results) / total, 2),
            variant_b_avg_score=round(sum(r.variant_b_score for r in results) / total, 2),
            variant_b_win_rate=round(b_wins / total, 2),
            position_consistency_rate=round(consistent_count / total, 2),
            avg_confidence=round(sum(r.confidence for r in results) / total, 2),
            non_interference_compliance_rate_a=round(sum(1 for r in results if r.passed_non_interference_a) / total, 2),
            non_interference_compliance_rate_b=round(sum(1 for r in results if r.passed_non_interference_b) / total, 2),
            adversarial_catch_rate_c=round(adversarial_catches / total, 2),
            details=results,
            fast_path_short_circuit_rate=fast_path_rate,
            token_reduction_pct=token_reduction,
            estimated_cost_savings_pct=token_reduction,
        )
