from dataclasses import dataclass

import pandas as pd

from ai_nutritionist.profile import NutritionProfile


@dataclass(frozen=True)
class MealTarget:
    calories: float
    protein_g: float
    fiber_g: float
    sodium_mg_limit: float
    saturated_fat_g_limit: float
    sugars_g_limit: float


MEAL_FRACTIONS = {
    "Breakfast": 0.25,
    "Lunch": 0.35,
    "Dinner": 0.40,
}


def meal_target(profile: NutritionProfile, meal_name: str) -> MealTarget:
    fraction = MEAL_FRACTIONS[meal_name]
    return MealTarget(
        calories=profile.daily_targets.calories * fraction,
        protein_g=profile.daily_targets.protein_g * fraction,
        fiber_g=profile.daily_targets.fiber_g * fraction,
        sodium_mg_limit=profile.daily_targets.sodium_mg_limit * fraction,
        saturated_fat_g_limit=profile.daily_targets.saturated_fat_g_limit * fraction,
        sugars_g_limit=profile.daily_targets.sugars_g_limit * fraction,
    )


def score_foods(foods: pd.DataFrame, profile: NutritionProfile, meal_name: str) -> pd.DataFrame:
    if foods.empty:
        result = foods.copy()
        result["score"] = []
        return result

    target = meal_target(profile, meal_name)
    scored = foods.copy()
    calories = scored["calories"].clip(lower=1)

    protein_density = (scored["protein_g"] / calories) * 100
    fiber_density = (scored["fiber_g"] / calories) * 100
    sodium_density = scored["sodium_mg"] / calories
    saturated_density = scored["saturated_fat_g"] / calories
    sugar_density = scored["sugars_g"] / calories

    meal_match = scored["meal_tags"].str.lower().str.contains(meal_name.lower()).astype(float)
    calorie_fit = 1 - ((scored["calories"] - (target.calories / 3)).abs() / max(target.calories, 1)).clip(0, 1)
    minimally_processed = scored["minimally_processed"].astype(float)

    score = (
        23 * _bounded(protein_density, 0.02, 0.18)
        + 21 * _bounded(fiber_density, 0.0, 0.07)
        + 17 * calorie_fit
        + 14 * minimally_processed
        + 10 * meal_match
        + 8 * (1 - _bounded(sodium_density, 0.0, 4.0))
        + 5 * (1 - _bounded(saturated_density, 0.0, 0.04))
        + 8 * (1 - _bounded(sugar_density, 0.0, 0.14))
    )

    if profile.bmi.category_id in {0, 1}:
        score += 6 * _bounded(scored["calories"], 80, 350)
    elif profile.bmi.category_id in {3, 4}:
        score += 6 * (1 - _bounded(scored["calories"], 80, 350))

    scored["score"] = score.round(3)
    return scored.sort_values(["score", "protein_g", "fiber_g"], ascending=[False, False, False]).reset_index(drop=True)


def _bounded(series: pd.Series, low: float, high: float) -> pd.Series:
    if high <= low:
        return series * 0
    return ((series - low) / (high - low)).clip(0, 1)


def nutrition_totals(items: list[dict[str, object]]) -> dict[str, float]:
    keys = [
        "calories",
        "protein_g",
        "carbohydrate_g",
        "fat_g",
        "fiber_g",
        "sugars_g",
        "sodium_mg",
        "saturated_fat_g",
    ]
    totals = {key: 0.0 for key in keys}
    for item in items:
        for key in keys:
            totals[key] += _as_float(item.get(key, 0))
    return {key: round(value, 1) for key, value in totals.items()}


def _as_float(value: object) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value)  # type: ignore[arg-type]
