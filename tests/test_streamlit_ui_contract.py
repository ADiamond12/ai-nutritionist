from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _ui_source() -> str:
    sources = [ROOT.joinpath("app.py").read_text(encoding="utf-8")]
    ui_dir = ROOT / "ai_nutritionist" / "ui"
    if ui_dir.exists():
        sources.extend(path.read_text(encoding="utf-8") for path in sorted(ui_dir.glob("*.py")))
    return "\n".join(sources)


def test_streamlit_requires_user_action_before_generating_plan():
    app_source = _ui_source()

    assert "Auto-generate" not in app_source
    assert "should_generate = submitted" in app_source
    assert 'initial_sidebar_state="expanded"' in app_source


def test_streamlit_hides_internal_plan_fit_scores_from_customer_ui():
    app_source = _ui_source()

    assert "Plan Fit" not in app_source
    assert "Ranker:" not in app_source
    assert "quality_score" not in app_source
    assert '"neural_score"' not in app_source


def test_streamlit_feedback_is_local_and_session_based():
    app_source = _ui_source()

    assert "st.feedback" in app_source
    assert "feedback_log" in app_source
    assert "st.session_state" in app_source
    assert "Download feedback CSV" in app_source
    assert "not uploaded" in app_source
    assert "Regenerate with feedback" in app_source


def test_streamlit_exposes_grocery_list_export_without_internal_scores():
    app_source = _ui_source()

    assert "Grocery List" in app_source
    assert "Download grocery CSV" in app_source
    assert "build_grocery_list" in app_source
    assert "grocery_list_csv" in app_source
