from pathlib import Path

from ai_nutritionist.feedback import FeedbackEntry, FeedbackStore


def test_feedback_store_round_trips_entries_and_exports_csv(tmp_path: Path):
    store = FeedbackStore(tmp_path / "feedback.sqlite")
    entry = FeedbackEntry(
        scope="meal",
        label="Dinner",
        sentiment="not_liked",
        dietary_pattern="mediterranean",
        weight_goal="lose",
        avoid_terms=["cod", "tomato"],
    )

    count = store.add(entry)
    entries = store.list_entries()
    csv_text = store.to_csv()

    assert count == 1
    assert entries[0].label == "Dinner"
    assert entries[0].avoid_terms == ["cod", "tomato"]
    assert "scope,label,sentiment,dietary_pattern,weight_goal,avoid_terms" in csv_text
