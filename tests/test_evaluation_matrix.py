from ai_nutritionist.evaluation import evaluate_profiles


def test_evaluation_matrix_reports_guidance_alignment_for_bmi_and_age_profiles():
    report = evaluate_profiles()

    assert len(report.rows) >= 5
    assert report.summary["profiles_evaluated"] == len(report.rows)
    assert report.summary["average_quality_score"] >= 65
    assert report.summary["profiles_with_protein_each_meal"] == len(report.rows)
    assert report.summary["profiles_with_produce_each_meal"] == len(report.rows)

    labels = {row.bmi_category for row in report.rows}
    assert {"Underweight", "Normal", "Overweight", "Severely overweight"}.issubset(labels)
    assert any(row.dietary_pattern == "mediterranean" for row in report.rows)
    assert any(row.dietary_pattern == "vegan" for row in report.rows)
    assert any(row.dietary_pattern == "vegetarian" for row in report.rows)
    assert any(row.dietary_pattern == "keto_style" for row in report.rows)
