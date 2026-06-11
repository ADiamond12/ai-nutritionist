from ai_nutritionist.evaluation import compare_planners, evaluate_profiles


def test_evaluation_matrix_reports_guidance_alignment_for_bmi_and_age_profiles():
    report = evaluate_profiles()

    assert len(report.rows) >= 5
    assert report.summary["profiles_evaluated"] == len(report.rows)
    assert report.summary["profiles_with_protein_each_meal"] == len(report.rows)
    assert report.summary["profiles_with_produce_each_meal"] == len(report.rows)
    assert report.summary["profiles_with_structure_feasible"] == len(report.rows)
    assert report.summary["profiles_with_daily_sodium_guardrail"] == len(report.rows)
    assert report.summary["profiles_with_sodium_guardrails"] == len(report.rows)

    labels = {row.bmi_category for row in report.rows}
    assert {"Underweight", "Normal", "Overweight", "Severely overweight"}.issubset(labels)
    assert any(row.dietary_pattern == "mediterranean" for row in report.rows)
    assert any(row.dietary_pattern == "vegan" for row in report.rows)
    assert any(row.dietary_pattern == "vegetarian" for row in report.rows)
    assert any(row.dietary_pattern == "keto_style" for row in report.rows)
    assert report.summary["average_calorie_delta_pct"] <= 12
    assert report.summary["meal_sodium_pass_rate_pct"] == 100.0
    assert all(row.calorie_delta_pct >= 0 for row in report.rows)
    assert all(row.protein_coverage_pct >= 80 for row in report.rows)
    assert all(row.fiber_coverage_pct >= 70 for row in report.rows)


def test_hybrid_v2_benchmark_improves_legacy_without_structure_regression():
    comparison = compare_planners()

    assert comparison["profiles_evaluated"] == len(evaluate_profiles().rows)
    assert comparison["hybrid_average_calorie_delta_pct"] <= comparison["legacy_average_calorie_delta_pct"]
    assert comparison["hybrid_meal_sodium_pass_rate_pct"] >= comparison["legacy_meal_sodium_pass_rate_pct"]
    assert comparison["hybrid_structure_feasibility_rate_pct"] == 100.0
    assert comparison["legacy_structure_feasibility_rate_pct"] == 100.0
    assert comparison["profiles_changed_by_hybrid_v2"] >= 1
