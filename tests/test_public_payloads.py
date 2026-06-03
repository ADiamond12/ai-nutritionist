from ai_nutritionist.plan_outputs import build_grocery_list, grocery_list_csv
from ai_nutritionist.presentation import public_daily_payload, public_weekly_payload
from ai_nutritionist.recommender import recommend, recommend_week


def test_public_daily_payload_hides_internal_scores_and_adds_grocery_list():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        dietary_pattern="mediterranean",
        weight_goal="lose",
        top_k=3,
    )

    payload = public_daily_payload(result)
    text = str(payload)

    assert payload["system_name"] == "AI Nutritionist"
    assert payload["grocery_list"]
    assert payload["daily_targets"]["calories"] == result.daily_targets.calories
    assert "quality_score" not in text
    assert "neural_score" not in text
    assert "model_name" not in text
    assert "score" not in payload["meals"][0]["items"][0]


def test_public_weekly_payload_contains_days_and_weekly_grocery_list():
    weekly = recommend_week(
        weight_kg=125,
        height_cm=200,
        age=30,
        sex="male",
        dietary_pattern="mediterranean",
        weight_goal="lose",
        top_k=3,
    )

    payload = public_weekly_payload(weekly)
    text = str(payload)

    assert len(payload["days"]) == 7
    assert payload["grocery_list"]
    assert payload["weekly_averages"]["calories"] > 0
    assert "quality_score" not in text
    assert "neural_score" not in text
    assert "model_name" not in text


def test_grocery_list_groups_duplicate_foods_and_exports_csv():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        dietary_pattern="mediterranean",
        weight_goal="maintain",
        top_k=3,
    )

    grocery_list = build_grocery_list(result)
    csv_text = grocery_list_csv(grocery_list)

    assert grocery_list
    assert all(item["serving_grams"] > 0 for item in grocery_list)
    assert all(item["times_used"] >= 1 for item in grocery_list)
    assert "food_group,food_name,serving_grams,times_used" in csv_text
