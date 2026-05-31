from ai_nutritionist.profile import build_profile
from ai_nutritionist.recommender import recommend


def test_body_fat_percentage_raises_protein_target_from_lean_mass():
    without_body_fat = build_profile(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate")
    with_body_fat = build_profile(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        body_fat_pct=18,
    )

    assert with_body_fat.body_fat_pct == 18
    assert with_body_fat.lean_body_mass_kg == 61.5
    assert with_body_fat.daily_targets.protein_g > without_body_fat.daily_targets.protein_g


def test_keto_style_plan_limits_carbs_and_uses_fat_forward_food_groups():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="keto_style",
        goal_focus="higher_protein",
        body_fat_pct=18,
        top_k=4,
    )

    assert result.preferences["dietary_pattern"] == "keto_style"
    assert result.daily_totals["carbohydrate_g"] <= 95
    assert result.macro_percentages["fat_pct"] >= result.macro_percentages["carbohydrate_pct"]
    for meal in result.meals:
        groups = {item["food_group"] for item in meal.items}
        assert "whole_grain" not in groups
        assert meal.guidance_checks["carbs_within_meal_limit"]
        assert meal.quality_score >= 98


def test_default_omnivore_and_vegan_plan_fit_scores_reach_98_plus():
    omnivore = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate", top_k=4)
    vegan = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        dietary_pattern="vegan",
        top_k=4,
    )

    assert min(meal.quality_score for meal in omnivore.meals) >= 98
    assert min(meal.quality_score for meal in vegan.meals) >= 98
    assert max(meal.quality_score for meal in omnivore.meals) <= 99.5
    assert max(meal.quality_score for meal in vegan.meals) <= 99.5


def test_macro_percentages_sum_to_about_100():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate", top_k=4)

    total = (
        result.macro_percentages["protein_pct"]
        + result.macro_percentages["carbohydrate_pct"]
        + result.macro_percentages["fat_pct"]
    )
    assert 99 <= total <= 101
