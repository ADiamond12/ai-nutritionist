from dataclasses import dataclass

from ai_nutritionist.guidelines import (
    GENERAL_FIBER_TARGET_G,
    MALE_FIBER_TARGET_G,
    SATURATED_FAT_MAX_ENERGY_PCT,
    SODIUM_LIMIT_MG,
    SUGAR_REFERENCE_ENERGY_PCT,
)
from ai_nutritionist.metrics import BMIResult, calculate_bmi


@dataclass(frozen=True)
class DailyTargets:
    calories: int
    protein_g: float
    fiber_g: float
    sodium_mg_limit: float
    saturated_fat_g_limit: float
    sugars_g_limit: float


@dataclass(frozen=True)
class NutritionProfile:
    weight_kg: float
    height_cm: float
    age: int
    sex: str
    activity: str
    weight_goal: str
    body_fat_pct: float | None
    lean_body_mass_kg: float | None
    bmi: BMIResult
    profile_goal: str
    daily_targets: DailyTargets


ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}

WEIGHT_GOALS = {"auto", "maintain", "lose", "gain"}


def build_profile(
    weight_kg: float,
    height_cm: float,
    age: int,
    *,
    sex: str = "unspecified",
    activity: str = "moderate",
    weight_goal: str = "auto",
    body_fat_pct: float | None = None,
) -> NutritionProfile:
    if age <= 0:
        raise ValueError("age must be greater than zero")

    sex = sex.lower().strip()
    activity = activity.lower().strip()
    weight_goal = weight_goal.lower().strip().replace(" ", "_")
    if sex not in {"female", "male", "unspecified"}:
        raise ValueError("sex must be female, male, or unspecified")
    if activity not in ACTIVITY_FACTORS:
        raise ValueError("activity must be sedentary, light, moderate, or active")
    if weight_goal not in WEIGHT_GOALS:
        raise ValueError("weight_goal must be auto, maintain, lose, or gain")
    if body_fat_pct is not None and not 5 <= body_fat_pct <= 60:
        raise ValueError("body_fat_pct must be between 5 and 60 when provided")

    bmi = calculate_bmi(weight_kg=weight_kg, height_cm=height_cm)
    lean_body_mass_kg = _lean_body_mass(weight_kg, body_fat_pct)
    energy_weight = _energy_weight(weight_kg, height_cm, bmi.category_id)
    base_calories = _estimate_energy(energy_weight, height_cm, age, sex, activity)
    goal, calorie_adjustment = _goal_from_bmi(bmi.category_id, weight_goal, base_calories)
    calories = _clamp_calories(base_calories + calorie_adjustment, sex)

    protein_factor = 1.0 if age >= 60 or bmi.category_id in {0, 1, 3, 4} else 0.8
    protein_g = max(50.0, round(weight_kg * protein_factor, 1))
    if lean_body_mass_kg is not None:
        protein_g = max(protein_g, round(lean_body_mass_kg * 1.6, 1))
    fiber_g = MALE_FIBER_TARGET_G if sex == "male" and age < 50 else GENERAL_FIBER_TARGET_G
    sodium_limit = SODIUM_LIMIT_MG
    saturated_fat_limit = round((calories * (SATURATED_FAT_MAX_ENERGY_PCT / 100)) / 9, 1)
    sugars_limit = round((calories * (SUGAR_REFERENCE_ENERGY_PCT / 100)) / 4, 1)

    return NutritionProfile(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        sex=sex,
        activity=activity,
        weight_goal=weight_goal,
        body_fat_pct=body_fat_pct,
        lean_body_mass_kg=lean_body_mass_kg,
        bmi=bmi,
        profile_goal=goal,
        daily_targets=DailyTargets(
            calories=calories,
            protein_g=protein_g,
            fiber_g=fiber_g,
            sodium_mg_limit=sodium_limit,
            saturated_fat_g_limit=saturated_fat_limit,
            sugars_g_limit=sugars_limit,
        ),
    )


def _estimate_energy(weight_kg: float, height_cm: float, age: int, sex: str, activity: str) -> int:
    if sex == "male":
        resting = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    elif sex == "female":
        resting = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        resting = 10 * weight_kg + 6.25 * height_cm - 5 * age - 78
    return round(resting * ACTIVITY_FACTORS[activity])


def _energy_weight(weight_kg: float, height_cm: float, category_id: int) -> float:
    if category_id not in {3, 4}:
        return weight_kg

    upper_reference_weight = 25 * ((height_cm / 100) ** 2)
    if weight_kg <= upper_reference_weight:
        return weight_kg
    return upper_reference_weight + ((weight_kg - upper_reference_weight) * 0.25)


def _lean_body_mass(weight_kg: float, body_fat_pct: float | None) -> float | None:
    if body_fat_pct is None:
        return None
    return round(weight_kg * (1 - (body_fat_pct / 100)), 1)


def _goal_from_bmi(category_id: int, weight_goal: str = "auto", base_calories: int | None = None) -> tuple[str, int]:
    if weight_goal == "maintain":
        return "maintain weight", 0
    if weight_goal == "lose":
        return "support gradual weight reduction", -_loss_deficit(base_calories or 2200, category_id)
    if weight_goal == "gain":
        return "support gradual weight gain", 250

    if category_id in {0, 1}:
        return "support gradual weight gain", 250
    if category_id == 2:
        return "maintain balanced intake", 0
    if category_id == 3:
        return "support gradual weight reduction", -250
    return "support gradual weight reduction", -400


def _loss_deficit(base_calories: int, category_id: int) -> int:
    lower = 350 if category_id <= 2 else 500
    upper = 700 if category_id <= 2 else 900
    target_deficit = round(base_calories * 0.25)
    return int(max(lower, min(upper, target_deficit)))


def _clamp_calories(calories: int, sex: str) -> int:
    floor = 1200 if sex == "female" else 1400
    return max(floor, min(3200, calories))
