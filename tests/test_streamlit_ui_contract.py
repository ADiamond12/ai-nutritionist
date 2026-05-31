from pathlib import Path


def test_streamlit_requires_user_action_before_generating_plan():
    app_source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(encoding="utf-8")

    assert "Auto-generate" not in app_source
    assert "should_generate = submitted" in app_source


def test_streamlit_hides_internal_plan_fit_scores_from_customer_ui():
    app_source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(encoding="utf-8")

    assert "Plan Fit" not in app_source
    assert "quality_score" not in app_source
    assert '"neural_score"' not in app_source
