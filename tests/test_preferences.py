from ai_nutritionist.recommender import recommend


def _all_recommendation_items(result):
    items = []
    for meal in result.meals:
        items.extend(meal.items)
        for alternatives in meal.alternatives.values():
            items.extend(alternatives)
    return items


def test_avoid_terms_remove_matching_foods_from_plan_and_alternatives():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="omnivore",
        avoid_terms=["fish", "chicken"],
        top_k=4,
    )

    names = " ".join(item["food_name"].lower() for item in _all_recommendation_items(result))
    assert "fish" not in names
    assert "chicken" not in names
    assert result.preferences["avoid_terms"] == ["fish", "chicken"]

    selected_families = [
        item["food_name"].split(",")[0].strip().lower()
        for meal in result.meals
        for item in meal.items
    ]
    assert len(selected_families) == len(set(selected_families))


def test_preferred_terms_boost_available_foods_into_plan():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="omnivore",
        preferred_terms=["salmon"],
        top_k=4,
    )

    lunch_dinner_names = " ".join(
        item["food_name"].lower()
        for meal in result.meals
        if meal.name in {"Lunch", "Dinner"}
        for item in meal.items
    )
    assert "salmon" in lunch_dinner_names
    assert result.preferences["preferred_terms"] == ["salmon"]


def test_goal_focus_updates_ranking_and_daily_progress():
    balanced = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="omnivore",
        top_k=4,
    )
    lower_sodium = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="omnivore",
        goal_focus="lower_sodium",
        top_k=4,
    )

    assert lower_sodium.preferences["goal_focus"] == "lower_sodium"
    assert "sodium_pct" in lower_sodium.daily_progress
    assert lower_sodium.daily_totals["sodium_mg"] <= balanced.daily_totals["sodium_mg"]


def test_meal_alternatives_are_grouped_and_exclude_selected_items():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate", top_k=4)

    for meal in result.meals:
        selected_ids = {item["fdc_id"] for item in meal.items}
        assert meal.alternatives
        assert {"protein", "whole_grain"}.issubset(meal.alternatives)
        for alternatives in meal.alternatives.values():
            assert len(alternatives) <= 3
            assert all(item["fdc_id"] not in selected_ids for item in alternatives)
