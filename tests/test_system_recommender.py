from ai_nutritionist.recommender import recommend, recommend_week


def test_system_recommendations_are_structured_meal_plans_with_explanations():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate")

    assert result.system_name == "AI Nutritionist"
    assert "not medical advice" in result.safety_notice.lower()
    assert result.daily_targets.calories > 0
    assert [meal.name for meal in result.meals] == ["Breakfast", "Lunch", "Dinner"]

    for meal in result.meals:
        assert len(meal.items) >= 3
        assert 0 <= meal.quality_score <= 100
        assert meal.explanations
        groups = {item["food_group"] for item in meal.items}
        assert len(groups) >= 3
        assert meal.totals["calories"] > 0
        assert meal.guidance_checks["has_protein"]
        assert meal.guidance_checks["has_produce"]


def test_vegetarian_system_filter_returns_only_vegetarian_items():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="female",
        activity="light",
        dietary_pattern="vegetarian",
    )

    for meal in result.meals:
        assert meal.items
        assert all(item["vegetarian"] for item in meal.items)


def test_recommendations_change_between_low_and_high_bmi_profiles():
    low_bmi = recommend(weight_kg=52, height_cm=180, age=24, sex="male", activity="moderate")
    high_bmi = recommend(weight_kg=108, height_cm=180, age=45, sex="male", activity="moderate")

    assert low_bmi.daily_targets.calories > high_bmi.daily_targets.calories
    assert low_bmi.profile_goal == "support gradual weight gain"
    assert high_bmi.profile_goal == "support gradual weight reduction"
    assert low_bmi.to_dict() != high_bmi.to_dict()


def test_lunch_and_dinner_are_not_identical_for_omnivore_profile():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate")
    lunch = next(meal for meal in result.meals if meal.name == "Lunch")
    dinner = next(meal for meal in result.meals if meal.name == "Dinner")

    assert [item["fdc_id"] for item in lunch.items] != [item["fdc_id"] for item in dinner.items]


def test_recommend_week_builds_varied_mediterranean_rotation_with_practical_foods():
    weekly = recommend_week(
        weight_kg=125,
        height_cm=200,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="mediterranean",
        weight_goal="lose",
        top_k=4,
    )

    assert len(weekly.days) == 7
    assert [day.day_name for day in weekly.days] == [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    assert weekly.weight_goal == "lose"
    assert weekly.dietary_pattern == "mediterranean"

    all_names = " ".join(
        item["food_name"].lower()
        for day in weekly.days
        for meal in day.result.meals
        for item in meal.items
    )
    assert any(term in all_names for term in ["chicken", "souvlaki"])
    assert any(term in all_names for term in ["salmon", "cod", "tuna", "fish"])
    assert any(term in all_names for term in ["lentil", "fasolada", "chickpea", "gigantes", "bean"])
    assert "pumpkin seeds" not in all_names
    assert "flax seeds" not in all_names
    assert "sprouts" not in all_names

    assert weekly.weekly_averages["calories"] > 0
    assert weekly.variety_counts["poultry_days"] >= 1
    assert weekly.variety_counts["fish_days"] >= 2
    assert weekly.variety_counts["legume_days"] >= 2


def test_mediterranean_preferred_chicken_can_surface_in_daily_plan():
    result = recommend(
        weight_kg=88,
        height_cm=180,
        age=45,
        sex="male",
        activity="moderate",
        dietary_pattern="mediterranean",
        preferred_terms="chicken",
        top_k=4,
    )

    names = " ".join(item["food_name"].lower() for meal in result.meals for item in meal.items)
    assert "chicken" in names
