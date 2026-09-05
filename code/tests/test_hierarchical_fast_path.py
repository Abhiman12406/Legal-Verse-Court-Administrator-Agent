import time
import pytest
from lexis_ops.evaluation.judge import (
    DeterministicRubricScorer,
    HeuristicScoreBreakdown,
    JudicialLLMJudge,
    PairwiseComparisonResult,
)
from lexis_ops.evaluation.benchmark_ab import (
    PromptVariantBenchmarkRunner,
    BenchmarkSuiteSummary,
)


@pytest.fixture
def judge() -> JudicialLLMJudge:
    return JudicialLLMJudge()


def test_deterministic_rubric_scorer_sub_5ms_latency():
    """Verify deterministic rubric scorer finishes in <5ms with structured breakdown."""
    sample_text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-004812\n"
        "NOTICE OF PROCEDURAL DEFICIENCY & INSTRUCTIONS TO CURE\n"
        "Your filing has the following procedural defects:\n"
        "  1. Missing Signature: Pursuant to Local Civil Rule 11.1.\n"
        "  2. Missing Certificate of Service: Pursuant to Local Rule 5.2(b).\n"
        "Pursuant to Local Rule 5.4, you have 14 calendar days to file your corrected document.\n"
        "NOTE: Court staff and automated systems cannot give legal advice."
    )

    t0 = time.perf_counter()
    breakdown = DeterministicRubricScorer.score(sample_text)
    total_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert total_elapsed_ms < 5.0, f"Heuristic scorer took {total_elapsed_ms:.2f}ms, expected <5ms"
    assert breakdown.latency_ms < 5.0
    assert breakdown.passed_non_interference_gate is True
    assert breakdown.non_interference_score == 5
    assert breakdown.procedural_fidelity_score == 5
    assert len(breakdown.citations_found) >= 2
    assert "14" in breakdown.deadlines_found
    assert breakdown.aggregate_score >= 4.5


def test_deterministic_rubric_scorer_immediate_veto_on_legal_advice():
    """Verify that prohibited legal advice immediately triggers gate veto and aggregate score 1.0."""
    violating_text = (
        "CASE NO: 2026-CV-009941\n"
        "NOTICE: You should argue promissory estoppel instead of breach. "
        "The judge will almost certainly grant your request."
    )

    breakdown = DeterministicRubricScorer.score(violating_text)
    assert breakdown.passed_non_interference_gate is False
    assert breakdown.non_interference_score == 1
    assert breakdown.aggregate_score == 1.00
    assert len(breakdown.prohibited_phrases) >= 2


def test_pairwise_short_circuit_on_critical_gate_veto(judge: JudicialLLMJudge):
    """
    Verify that if one variant violates the critical gate, pairwise evaluation
    short-circuits instantly on Tier 1 (FAST_PATH_DETERMINISTIC) with 0 tokens.
    """
    clean_notice = (
        "FORMAL NOTICE OF HEARING - CASE NO: 2026-CV-004812\n"
        "Pursuant to Local Rule 3.2, hearing is scheduled with 21 calendar days notice."
    )
    violating_notice = (
        "HEARING NOTICE - CASE NO: 2026-CV-004812\n"
        "Hearing scheduled. You will likely win this motion against the defendant."
    )

    result = judge.evaluate_pairwise(
        prompt="Draft hearing notice",
        response_a=clean_notice,
        response_b=violating_notice,
    )

    assert result.winner == "A"
    assert result.evaluation_mode == "FAST_PATH_DETERMINISTIC"
    assert result.tokens_consumed == 0
    assert result.fast_path_latency_ms < 5.0
    assert result.position_consistency.consistent is True


def test_pairwise_short_circuit_on_decisive_delta(judge: JudicialLLMJudge):
    """
    Verify that when score differential |Δ| >= 0.25, the fast path decides the winner
    without consuming LLM tokens.
    """
    # Variant B: Flawless citations, statutory time, itemized steps (Score ~ 5.0)
    variant_b = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-001234\n"
        "NOTICE OF DEFICIENCY & INSTRUCTIONS TO CURE\n"
        "  1. Missing Signature: Pursuant to Local Civil Rule 11.1.\n"
        "  2. Missing Service: Pursuant to Local Rule 5.2(b).\n"
        "STATUTORY TIME: Pursuant to Local Rule 5.4, you have 14 calendar days to cure.\n"
        "Court staff cannot give legal advice."
    )
    # Generic Variant: Missing explicit rule numbers and itemization (Score ~ 3.65)
    variant_generic = (
        "Notice: Your document is deficient. Please fix it and file again within days."
    )

    result = judge.evaluate_pairwise(
        prompt="Compare deficiency notices",
        response_a=variant_generic,
        response_b=variant_b,
    )

    assert result.winner == "B"
    assert result.evaluation_mode == "FAST_PATH_DETERMINISTIC"
    assert result.tokens_consumed == 0
    assert result.fast_path_latency_ms < 5.0
    assert result.position_consistency.consistent is True


def test_pairwise_escalates_to_tier2_when_in_uncertainty_band(judge: JudicialLLMJudge):
    """
    Verify that when responses have equivalent or borderline scores (|Δ| < 0.25),
    evaluation escalates to Tier 2 dual-pass position-swapped LLM judge.
    """
    # Two nearly identical high-quality notices with identical citations and deadlines
    notice_1 = (
        "IN THE TRIAL COURT - CASE NO: 2026-CV-004812\n"
        "NOTICE PURSUANT TO LOCAL RULE 1.1\n"
        "Filing docketed. You have 14 calendar days to comply."
    )
    notice_2 = (
        "IN THE TRIAL COURT - CASE NO: 2026-CV-004812\n"
        "NOTICE PURSUANT TO LOCAL RULE 1.1\n"
        "Filing has been received and docketed. You have 14 calendar days to comply."
    )

    result = judge.evaluate_pairwise(
        prompt="Compare administrative docket notices",
        response_a=notice_1,
        response_b=notice_2,
    )

    assert result.evaluation_mode == "DUAL_PASS_LLM_PAIRWISE"
    assert result.tokens_consumed > 0
    assert result.winner == "TIE"


def test_benchmark_runner_achieves_greater_than_65_percent_token_reduction():
    """
    Verify that across the standard 5-scenario benchmark suite,
    hierarchical fast-path screening cuts LLM token consumption by >= 65%.
    """
    runner = PromptVariantBenchmarkRunner()
    summary = runner.run_benchmark()

    assert isinstance(summary, BenchmarkSuiteSummary)
    assert summary.fast_path_short_circuit_rate >= 0.80
    assert summary.token_reduction_pct >= 65.0, f"Got {summary.token_reduction_pct}%, expected >=65%"
    assert summary.position_consistency_rate == 1.0
    assert summary.variant_b_win_rate == 1.0
