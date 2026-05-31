import pandas as pd

from ai_nutritionist.profile import build_profile
from ai_nutritionist.scoring import score_foods


def test_profile_targets_shift_with_bmi_and_age():
    underweight = build_profile(weight_kg=58, height_cm=180, age=24, sex="male", activity="moderate")
    normal = build_profile(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate")
    obese_older = build_profile(weight_kg=108, height_cm=180, age=67, sex="male", activity="moderate")

    assert underweight.bmi.category_label == "Underweight"
    assert normal.bmi.category_label == "Normal"
    assert obese_older.bmi.category_label == "Severely overweight"
    assert underweight.daily_targets.calories > normal.daily_targets.calories
    assert obese_older.daily_targets.calories < normal.daily_targets.calories
    assert obese_older.daily_targets.protein_g >= normal.daily_targets.protein_g


def test_profile_accepts_explicit_weight_goal_over_bmi_default():
    auto = build_profile(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate")
    maintain = build_profile(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        weight_goal="maintain",
    )
    lose = build_profile(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        weight_goal="lose",
    )
    gain = build_profile(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        activity="moderate",
        weight_goal="gain",
    )

    assert auto.weight_goal == "auto"
    assert maintain.weight_goal == "maintain"
    assert maintain.profile_goal == "maintain weight"
    assert lose.profile_goal == "support gradual weight reduction"
    assert gain.profile_goal == "support gradual weight gain"
    assert lose.daily_targets.calories < maintain.daily_targets.calories < gain.daily_targets.calories


def test_explicit_lose_goal_uses_bounded_deficit_for_large_profiles():
    maintain = build_profile(
        weight_kg=120,
        height_cm=205,
        age=30,
        sex="male",
        activity="moderate",
        weight_goal="maintain",
    )
    lose = build_profile(
        weight_kg=120,
        height_cm=205,
        age=30,
        sex="male",
        activity="moderate",
        weight_goal="lose",
    )

    assert 2500 <= lose.daily_targets.calories <= 2650
    assert maintain.daily_targets.calories - lose.daily_targets.calories >= 500
    assert maintain.daily_targets.calories - lose.daily_targets.calories <= 900


def test_scoring_prefers_fiber_rich_lower_sodium_foods_when_otherwise_similar():
    foods = pd.DataFrame(
        [
            {
                "food_name": "Refined salty grain",
                "food_group": "whole_grain",
                "meal_tags": "lunch,dinner",
                "calories": 180,
                "protein_g": 5,
                "carbohydrate_g": 36,
                "fat_g": 2,
                "fiber_g": 1,
                "sugars_g": 2,
                "sodium_mg": 650,
                "saturated_fat_g": 0.3,
                "minimally_processed": 0,
            },
            {
                "food_name": "Higher fiber grain",
                "food_group": "whole_grain",
                "meal_tags": "lunch,dinner",
                "calories": 180,
                "protein_g": 6,
                "carbohydrate_g": 34,
                "fat_g": 2,
                "fiber_g": 6,
                "sugars_g": 1,
                "sodium_mg": 15,
                "saturated_fat_g": 0.2,
                "minimally_processed": 1,
            },
        ]
    )
    profile = build_profile(weight_kg=75, height_cm=180, age=35)

    scored = score_foods(foods, profile, meal_name="Lunch")

    assert scored.iloc[0]["food_name"] == "Higher fiber grain"
    assert scored.iloc[0]["score"] > scored.iloc[1]["score"]
