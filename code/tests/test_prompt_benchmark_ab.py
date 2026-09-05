from __future__ import annotations

import pytest
from lexis_ops.evaluation.benchmark_ab import (
    PromptVariantBenchmarkRunner,
    BenchmarkSuiteSummary,
)


def test_prompt_variant_ab_benchmark_execution():
    runner = PromptVariantBenchmarkRunner()
    summary = runner.run_benchmark()

    assert isinstance(summary, BenchmarkSuiteSummary)
    assert summary.total_scenarios == 5

    # 1. Variant B (Modern Plain Language) should outperform or tie Variant A (Traditional Archaic)
    assert summary.variant_b_avg_score >= summary.variant_a_avg_score

    # 2. Position bias mitigation: 100% position consistency across swapped passes
    assert summary.position_consistency_rate == 1.0

    # 3. Substantive non-interference compliance: Both neutral variants pass 100%
    assert summary.non_interference_compliance_rate_a == 1.0
    assert summary.non_interference_compliance_rate_b == 1.0

    # 4. Critical Gate: 100% catch rate on adversarial over-advising variant (Variant C)
    assert summary.adversarial_catch_rate_c == 1.0

    # 5. Average confidence should reflect calibrated score differential (>= 0.70)
    assert summary.avg_confidence >= 0.70
