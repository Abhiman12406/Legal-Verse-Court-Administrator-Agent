from __future__ import annotations

import pytest
from lexis_ops.evaluation.judge import (
    JUDICIAL_RUBRICS,
    DirectEvaluationResult,
    JudicialLLMJudge,
    PairwiseComparisonResult,
)


@pytest.fixture
def judge() -> JudicialLLMJudge:
    return JudicialLLMJudge()


# =========================================================================
# Procedure 1 Test Suite: Judicial LLM-as-Judge & Rubrics
# =========================================================================

def test_direct_scoring_compliant_procedural_notice(judge: JudicialLLMJudge):
    """Verifies direct scoring of a fully compliant procedural notice with evidence-first reasoning."""
    notice_text = (
        "IN THE TRIAL COURT OF THE JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-004812\n\n"
        "NOTICE OF PROCEDURAL DEFICIENCY\n"
        "Pursuant to Local Civil Rule 11.1, the filing entitled 'Motion to Dismiss' lacks a valid signature block.\n"
        "Pursuant to Local Rule 5.4, the filing party is granted 14 calendar days to cure all cited defects.\n"
        "CLERK OF COURT / AUTOMATED DOCKET GATEWAY"
    )
    schema_payload = {
        "case_number": "2026-CV-004812",
        "document_title": "Motion to Dismiss",
        "notice_type": "NOTICE_OF_DEFICIENCY",
        "defects": [{"rule_citation": "Local Civil Rule 11.1"}],
    }

    result = judge.evaluate_direct(
        subject_id="notice-001",
        prompt="Generate deficiency notice for missing signature",
        response_text=notice_text,
        response_data=schema_payload,
    )

    assert isinstance(result, DirectEvaluationResult)
    assert result.passed_critical_gate is True
    assert result.aggregate_score >= 4.5
    # Verify evidence-first justification exists for each criterion
    for score in result.scores:
        assert len(score.evidence) > 0
        assert len(score.justification) > 10


def test_direct_scoring_prohibited_legal_advice_fails_critical_gate(judge: JudicialLLMJudge):
    """Verifies that offering substantive legal advice or outcome predictions immediately fails the critical gate."""
    violating_text = (
        "We reviewed your motion. You should argue equitable estoppel instead of laches. "
        "In my opinion the judge will likely grant your motion if you file an amended complaint."
    )

    result = judge.evaluate_direct(
        subject_id="violating-notice-002",
        prompt="Review filing and advise litigant",
        response_text=violating_text,
    )

    assert result.passed_critical_gate is False
    # Substantive non-interference score must be 1
    non_interference = next(s for s in result.scores if "Non-Interference" in s.criterion)
    assert non_interference.score == 1
    assert any("prohibited phrase" in e for e in non_interference.evidence)


def test_pairwise_comparison_position_swap_consistency(judge: JudicialLLMJudge):
    """
    Verifies pairwise comparison with dual-pass position swapping:
    Evaluates (A, B) and (B, A) to detect position bias and ensure consistent evaluation.
    """
    prompt = "Draft hearing notice for civil motion with ASL accommodation"

    # Response A: High quality, procedural citations, neutral tone
    response_a = (
        "FORMAL NOTICE OF HEARING - CASE NO: 2026-CV-004812\n"
        "PLEASE TAKE NOTICE that a hearing is calendarized pursuant to Local Rule 3.2.\n"
        "Statutory notice: 21 calendar days provided. Court-certified ASL interpreter locked."
    )

    # Response B: Violates neutrality with outcome prediction
    response_b = (
        "HEARING NOTICE - CASE NO: 2026-CV-004812\n"
        "Hearing scheduled. You will likely win this motion against the defendant."
    )

    comparison = judge.evaluate_pairwise(
        prompt=prompt,
        response_a=response_a,
        response_b=response_b,
    )

    assert isinstance(comparison, PairwiseComparisonResult)
    assert comparison.winner == "A"
    assert comparison.position_consistency.consistent is True
    assert comparison.position_consistency.first_pass_winner == "A"
    assert comparison.position_consistency.second_pass_winner == "A"
    assert comparison.confidence >= 0.85


def test_pairwise_comparison_tie_resolution_on_equivalent_responses(judge: JudicialLLMJudge):
    """Verifies that equivalent responses are resolved as a calibrated TIE with 0.5 confidence."""
    prompt = "Administrative notice of docket receipt"
    response_a = "NOTICE: Your filing has been docketed pursuant to Local Rule 1.1 on September 4, 2026."
    response_b = "NOTICE: Your filing has been received and docketed pursuant to Local Rule 1.1 on September 4, 2026."

    comparison = judge.evaluate_pairwise(
        prompt=prompt,
        response_a=response_a,
        response_b=response_b,
    )

    assert comparison.winner == "TIE"
    assert comparison.confidence == 0.60 or comparison.confidence == 0.50
