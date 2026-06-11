from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from ai_nutritionist.constants import MEAL_NAMES, SAFETY_DISCLAIMER, SYSTEM_NAME
from ai_nutritionist.data import load_food_catalog
from ai_nutritionist.metrics import BMIResult
from ai_nutritionist.optimizer import (
    OptimizableMeal,
    PlanOptimizationSummary,
    optimize_daily_plan,
)
from ai_nutritionist.preferences import RecommendationPreferences, apply_preferences, build_preferences
from ai_nutritionist.profile import DailyTargets, build_profile
from ai_nutritionist.ranker import MODEL_NAME, rank_foods_with_neural_model
from ai_nutritionist.scoring import meal_target, nutrition_totals


MEAL_BLUEPRINTS = {
    "Breakfast": ["whole_grain", "protein", "fruit", "healthy_fat"],
    "Lunch": ["protein", "vegetable", "whole_grain", "healthy_fat"],
    "Dinner": ["protein", "vegetable", "whole_grain", "healthy_fat"],
}

KETO_STYLE_BLUEPRINTS = {
    "Breakfast": ["protein", "healthy_fat", "vegetable", "protein"],
    "Lunch": ["protein", "vegetable", "healthy_fat", "protein"],
    "Dinner": ["protein", "vegetable", "healthy_fat", "protein"],
}

COMMON_OMNIVORE_PROTEIN_TERMS = (
    "chicken breast",
    "turkey breast",
    "turkey, light",
    "fish, salmon",
    "fish, tuna",
    "fish, cod",
    "fish, tilapia",
    "fish, trout",
    "fish, snapper",
    "fish, halibut",
    "shrimp, steamed",
    "shrimp, grilled",
    "shrimp, baked",
    "shrimp scampi",
)

KETO_STYLE_EXCLUDE_TERMS = (
    "pork skin",
    "cracklings",
    "hot dog",
    "bacon strip, meatless",
    "breaded",
    "fried",
    "beaver",
    "bear",
    "squirrel",
    "opossum",
    "caribou",
)

LOW_PRACTICALITY_STANDALONE_TERMS = (
    "alfalfa sprouts",
    "pumpkin seeds",
    "flax seeds",
    "chia seeds",
    "sesame seeds",
    "sunflower seeds",
    "fruit dressing",
    "dressing",
)

MEDITERRANEAN_NON_CORE_TERMS = (
    "cassava",
    "cereal",
    "challah",
    "chappatti",
    "fufu",
    "kumquat",
    "passion fruit",
    "roti",
    "soybean",
    "soybeans",
    "starfruit",
    "tortilla",
)

SCALABLE_NUTRIENT_KEYS = (
    "serving_grams",
    "calories",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sugars_g",
    "sodium_mg",
    "saturated_fat_g",
)

PLANT_PROTEIN_TERMS = ("bean", "lentil", "fasolada", "chickpea", "gigantes", "hummus", "tofu", "tempeh", "pea")

WEEK_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

MEDITERRANEAN_WEEK_ROTATION = (
    ("poultry", ("chicken", "souvlaki")),
    ("fish", ("salmon", "fish")),
    ("legume", ("lentil", "fasolada", "beans")),
    ("fish", ("cod", "plaki", "fish")),
    ("legume", ("chickpea", "gigantes", "beans")),
    ("poultry", ("chicken lemon", "rice soup")),
    ("fish_legume", ("tuna and white bean", "white bean", "fish")),
)

GENERIC_WEEK_ROTATION = (
    ("poultry", ("chicken",)),
    ("fish", ("salmon", "fish")),
    ("legume", ("beans", "lentil")),
    ("poultry", ("turkey",)),
    ("fish", ("tuna", "fish")),
    ("legume", ("chickpea", "beans")),
    ("egg_dairy", ("egg", "yogurt")),
)

ALTERNATIVE_CANDIDATE_POOL = 8
PUBLIC_ALTERNATIVE_LIMIT = 3


@dataclass(frozen=True)
class MealRecommendation:
    name: str
    title: str
    items: list[dict[str, Any]]
    totals: dict[str, float]
    quality_score: float
    model_name: str
    guidance_checks: dict[str, bool]
    explanations: list[str]
    alternatives: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class RecommendationResult:
    system_name: str
    bmi: BMIResult
    age: int
    sex: str
    activity: str
    weight_goal: str
    body_fat_pct: float | None
    lean_body_mass_kg: float | None
    profile_goal: str
    daily_targets: DailyTargets
    health_summary: str
    safety_notice: str
    disclaimer: str
    preferences: dict[str, object]
    daily_totals: dict[str, float]
    daily_progress: dict[str, float]
    macro_percentages: dict[str, float]
    planner_summary: PlanOptimizationSummary
    meals: list[MealRecommendation]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WeeklyDayRecommendation:
    day_name: str
    rotation_focus: str
    result: RecommendationResult


@dataclass(frozen=True)
class WeeklyRecommendationResult:
    system_name: str
    dietary_pattern: str
    weight_goal: str
    nutrition_focus: str
    days: list[WeeklyDayRecommendation]
    weekly_totals: dict[str, float]
    weekly_averages: dict[str, float]
    variety_counts: dict[str, int]
    planner_summary: PlanOptimizationSummary
    safety_notice: str
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def recommend(
    weight_kg: float,
    height_cm: float,
    age: int,
    *,
    sex: str = "unspecified",
    activity: str = "moderate",
    dietary_pattern: str = "omnivore",
    body_fat_pct: float | None = None,
    weight_goal: str = "auto",
    goal_focus: str = "balanced",
    avoid_terms: str | list[str] | None = None,
    preferred_terms: str | list[str] | None = None,
    top_k: int = 4,
    veg_filter: int = -1,
    data_dir: Path | str | None = None,
    planner_mode: str = "hybrid_v2",
) -> RecommendationResult:
    if top_k < 3:
        top_k = 3
    if dietary_pattern not in {"mediterranean", "omnivore", "vegetarian", "vegan", "keto_style"}:
        raise ValueError("dietary_pattern must be mediterranean, omnivore, vegetarian, vegan, or keto_style")
    if planner_mode not in {"legacy", "hybrid_v2"}:
        raise ValueError("planner_mode must be legacy or hybrid_v2")

    profile = build_profile(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        sex=sex,
        activity=activity,
        weight_goal=weight_goal,
        body_fat_pct=body_fat_pct,
    )
    preferences = build_preferences(
        goal_focus=goal_focus,
        avoid_terms=avoid_terms,
        preferred_terms=preferred_terms,
    )
    catalog = load_food_catalog(data_dir)
    if dietary_pattern == "keto_style":
        catalog = _keto_style_catalog(catalog).reset_index(drop=True)
    elif dietary_pattern == "vegan":
        catalog = catalog.loc[catalog["vegan"]].reset_index(drop=True)
    elif dietary_pattern == "vegetarian" or veg_filter == 0:
        catalog = catalog.loc[catalog["vegetarian"]].reset_index(drop=True)
    elif veg_filter == 1:
        catalog = catalog.loc[~catalog["vegetarian"]].reset_index(drop=True)

    used_fdc_ids: set[int] = set()
    used_food_keys: set[str] = set()
    meals = [
        _build_meal(
            catalog,
            profile,
            meal_name,
            top_k,
            dietary_pattern,
            preferences,
            used_fdc_ids,
            used_food_keys,
            data_dir,
        )
        for meal_name in MEAL_NAMES
    ]
    meals = _align_portions_for_goal(meals, profile, dietary_pattern)
    planner_summary = PlanOptimizationSummary(
        planner_mode="legacy",
        optimized=False,
        substitutions=0,
        portion_adjustments=0,
        remaining_constraints=(),
    )
    if planner_mode == "hybrid_v2":
        meals, planner_summary = _optimize_meals(meals, profile, dietary_pattern, preferences.goal_focus)
    else:
        meals = [
            replace(meal, alternatives=_limit_alternatives(meal.alternatives))
            for meal in meals
        ]
    daily_totals = nutrition_totals([item for meal in meals for item in meal.items])

    return RecommendationResult(
        system_name=SYSTEM_NAME,
        bmi=profile.bmi,
        age=age,
        sex=profile.sex,
        activity=profile.activity,
        weight_goal=profile.weight_goal,
        body_fat_pct=profile.body_fat_pct,
        lean_body_mass_kg=profile.lean_body_mass_kg,
        profile_goal=profile.profile_goal,
        daily_targets=profile.daily_targets,
        health_summary=_health_summary(profile.bmi, profile.profile_goal),
        safety_notice=SAFETY_DISCLAIMER,
        disclaimer=SAFETY_DISCLAIMER,
        preferences={**preferences.to_dict(), "dietary_pattern": dietary_pattern, "weight_goal": profile.weight_goal},
        daily_totals=daily_totals,
        daily_progress=_daily_progress(daily_totals, profile.daily_targets),
        macro_percentages=_macro_percentages(daily_totals),
        planner_summary=planner_summary,
        meals=meals,
    )


def _optimize_meals(meals: list[MealRecommendation], profile, dietary_pattern: str, goal_focus: str):
    optimized = optimize_daily_plan(
        [
            OptimizableMeal(
                name=meal.name,
                items=meal.items,
                alternatives=meal.alternatives,
            )
            for meal in meals
        ],
        profile.daily_targets,
        {meal.name: meal_target(profile, meal.name) for meal in meals},
        dietary_pattern,
        goal_focus,
    )
    selected_ids = {
        int(item["fdc_id"])
        for optimized_meal in optimized.meals
        for item in optimized_meal.items
    }
    rebuilt = []
    for meal, optimized_meal in zip(meals, optimized.meals):
        items = optimized_meal.items
        totals = nutrition_totals(items)
        checks = _guidance_checks(items, totals, profile, meal.name, dietary_pattern)
        explanations = _explanations(items, checks, meal.name, dietary_pattern)
        if optimized.summary.optimized:
            explanations.append("Hybrid planning balanced the complete day across nutrition targets and guardrails.")
        rebuilt.append(
            replace(
                meal,
                title=_meal_title(meal.name, items, dietary_pattern),
                items=items,
                totals=totals,
                quality_score=_quality_score(checks, totals, profile, meal.name),
                guidance_checks=checks,
                explanations=explanations,
                alternatives=_exclude_selected_alternatives(meal.alternatives, selected_ids),
            )
        )
    return rebuilt, optimized.summary


def _exclude_selected_alternatives(
    alternatives: dict[str, list[dict[str, Any]]],
    selected_ids: set[int],
) -> dict[str, list[dict[str, Any]]]:
    return {
        group: [item for item in items if int(item["fdc_id"]) not in selected_ids][:PUBLIC_ALTERNATIVE_LIMIT]
        for group, items in alternatives.items()
        if any(int(item["fdc_id"]) not in selected_ids for item in items)
    }


def _limit_alternatives(alternatives: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {group: items[:PUBLIC_ALTERNATIVE_LIMIT] for group, items in alternatives.items() if items}


def _align_portions_for_goal(
    meals: list[MealRecommendation],
    profile,
    dietary_pattern: str,
) -> list[MealRecommendation]:
    daily_totals = nutrition_totals([item for meal in meals for item in meal.items])
    target_calories = max(float(profile.daily_targets.calories), 1.0)
    actual_calories = float(daily_totals["calories"])
    is_reduction_goal = profile.weight_goal == "lose" or "weight reduction" in profile.profile_goal
    is_gain_goal = profile.weight_goal == "gain" or "weight gain" in profile.profile_goal

    factor = 1.0
    if is_reduction_goal and actual_calories > target_calories * 1.08:
        factor = (target_calories * 1.03) / actual_calories
    elif not is_gain_goal and actual_calories > target_calories * 1.12:
        factor = (target_calories * 1.06) / actual_calories
    elif actual_calories < target_calories * 0.88:
        upward_alignment = 0.86 if dietary_pattern == "keto_style" else 0.90
        factor = (target_calories * upward_alignment) / actual_calories

    factor = max(0.72, min(1.60, factor))
    if abs(factor - 1.0) < 0.01:
        return meals

    if factor < 1:
        alignment_note = "Portions are scaled to stay closer to the selected weight-reduction energy target."
    else:
        alignment_note = "Portions are scaled to stay closer to the estimated daily energy target."

    scaled_meals = []
    for meal in meals:
        items = [_scale_food_record(item, factor) for item in meal.items]
        if dietary_pattern == "keto_style":
            items = _trim_keto_meal_carbs(items, meal.name)
            items = _trim_keto_meal_saturated_fat(items, profile, meal.name)
        totals = nutrition_totals(items)
        checks = _guidance_checks(items, totals, profile, meal.name, dietary_pattern)
        scaled_meals.append(
            replace(
                meal,
                items=items,
                totals=totals,
                guidance_checks=checks,
                quality_score=_quality_score(checks, totals, profile, meal.name),
                explanations=[
                    *meal.explanations,
                    alignment_note,
                ],
            )
        )
    return scaled_meals


def _scale_food_record(item: dict[str, Any], factor: float) -> dict[str, Any]:
    scaled = item.copy()
    for key in SCALABLE_NUTRIENT_KEYS:
        scaled[key] = round(float(scaled.get(key, 0) or 0) * factor, 1)
    scaled["Calories"] = scaled["calories"]
    scaled["Fats"] = scaled["fat_g"]
    scaled["Proteins"] = scaled["protein_g"]
    scaled["Carbohydrates"] = scaled["carbohydrate_g"]
    scaled["Fibre"] = scaled["fiber_g"]
    scaled["Sugars"] = scaled["sugars_g"]
    return scaled


def _trim_keto_meal_carbs(items: list[dict[str, Any]], meal_name: str) -> list[dict[str, Any]]:
    limit = _carbohydrate_limit("keto_style", meal_name)
    totals = nutrition_totals(items)
    if totals["carbohydrate_g"] <= limit:
        return items

    trimmed = [item.copy() for item in items]
    carb_order = sorted(
        range(len(trimmed)),
        key=lambda index: float(trimmed[index].get("carbohydrate_g", 0) or 0),
        reverse=True,
    )
    for index in carb_order:
        totals = nutrition_totals(trimmed)
        excess_carbs = totals["carbohydrate_g"] - limit
        if excess_carbs <= 0:
            break
        item_carbs = float(trimmed[index].get("carbohydrate_g", 0) or 0)
        if item_carbs <= 0:
            continue
        reduction = min(0.35, (excess_carbs / item_carbs) + 0.02)
        trimmed[index] = _scale_food_record(trimmed[index], 1 - reduction)
    return trimmed


def _trim_keto_meal_saturated_fat(items: list[dict[str, Any]], profile, meal_name: str) -> list[dict[str, Any]]:
    limit = meal_target(profile, meal_name).saturated_fat_g_limit
    totals = nutrition_totals(items)
    if totals["saturated_fat_g"] <= limit:
        return items

    trimmed = [item.copy() for item in items]
    saturated_fat_order = sorted(
        range(len(trimmed)),
        key=lambda index: float(trimmed[index].get("saturated_fat_g", 0) or 0),
        reverse=True,
    )
    for index in saturated_fat_order:
        totals = nutrition_totals(trimmed)
        excess_saturated_fat = totals["saturated_fat_g"] - limit
        if excess_saturated_fat <= 0:
            break
        item_saturated_fat = float(trimmed[index].get("saturated_fat_g", 0) or 0)
        if item_saturated_fat <= 0:
            continue
        reduction = min(0.30, (excess_saturated_fat / item_saturated_fat) + 0.02)
        trimmed[index] = _scale_food_record(trimmed[index], 1 - reduction)
    return trimmed


def recommend_week(
    weight_kg: float,
    height_cm: float,
    age: int,
    *,
    sex: str = "unspecified",
    activity: str = "moderate",
    dietary_pattern: str = "mediterranean",
    body_fat_pct: float | None = None,
    weight_goal: str = "auto",
    goal_focus: str = "balanced",
    avoid_terms: str | list[str] | None = None,
    preferred_terms: str | list[str] | None = None,
    top_k: int = 4,
    veg_filter: int = -1,
    data_dir: Path | str | None = None,
    days: int = 7,
    planner_mode: str = "hybrid_v2",
) -> WeeklyRecommendationResult:
    if days < 1 or days > 14:
        raise ValueError("days must be between 1 and 14")

    rotation = _weekly_rotation_for_pattern(dietary_pattern)
    planned_days: list[WeeklyDayRecommendation] = []
    for day_index in range(days):
        day_name = WEEK_DAY_NAMES[day_index % len(WEEK_DAY_NAMES)]
        rotation_focus, rotation_terms = rotation[day_index % len(rotation)]
        day_preferences = _merge_terms(preferred_terms, rotation_terms)
        result = recommend(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            sex=sex,
            activity=activity,
            dietary_pattern=dietary_pattern,
            body_fat_pct=body_fat_pct,
            weight_goal=weight_goal,
            goal_focus=goal_focus,
            avoid_terms=avoid_terms,
            preferred_terms=day_preferences,
            top_k=top_k,
            veg_filter=veg_filter,
            data_dir=data_dir,
            planner_mode=planner_mode,
        )
        planned_days.append(
            WeeklyDayRecommendation(day_name=day_name, rotation_focus=rotation_focus, result=result)
        )

    weekly_totals = _weekly_totals(planned_days)
    weekly_averages = {key: round(value / len(planned_days), 1) for key, value in weekly_totals.items()}
    return WeeklyRecommendationResult(
        system_name=SYSTEM_NAME,
        dietary_pattern=dietary_pattern,
        weight_goal=str(planned_days[0].result.preferences["weight_goal"]),
        nutrition_focus=goal_focus,
        days=planned_days,
        weekly_totals=weekly_totals,
        weekly_averages=weekly_averages,
        variety_counts=_weekly_variety_counts(planned_days),
        planner_summary=_weekly_planner_summary(planned_days),
        safety_notice=SAFETY_DISCLAIMER,
        disclaimer=SAFETY_DISCLAIMER,
    )


def _weekly_rotation_for_pattern(dietary_pattern: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if dietary_pattern == "mediterranean":
        return MEDITERRANEAN_WEEK_ROTATION
    if dietary_pattern == "vegan":
        return (
            ("legume", ("lentil", "beans")),
            ("soy", ("tofu", "soy")),
            ("legume", ("chickpea", "hummus")),
            ("grain_legume", ("quinoa", "beans")),
            ("legume", ("black beans", "beans")),
            ("soy", ("tempeh", "tofu")),
            ("legume", ("peas", "lentil")),
        )
    if dietary_pattern == "vegetarian":
        return (
            ("egg_dairy", ("egg", "yogurt")),
            ("legume", ("lentil", "beans")),
            ("dairy", ("cottage cheese", "yogurt")),
            ("legume", ("chickpea", "hummus")),
            ("soy", ("tofu", "soy")),
            ("egg_dairy", ("egg", "cheese")),
            ("legume", ("beans", "peas")),
        )
    if dietary_pattern == "keto_style":
        return (
            ("poultry", ("chicken",)),
            ("fish", ("salmon", "fish")),
            ("egg", ("egg",)),
            ("fish", ("tuna", "fish")),
            ("poultry", ("turkey",)),
            ("seafood", ("shrimp",)),
            ("dairy", ("cottage cheese", "cheese")),
        )
    return GENERIC_WEEK_ROTATION


def _merge_terms(base_terms: str | list[str] | None, extra_terms: tuple[str, ...]) -> list[str]:
    terms = []
    if isinstance(base_terms, str):
        raw_terms = base_terms.replace(";", ",").replace("\n", ",").split(",")
    elif base_terms is None:
        raw_terms = []
    else:
        raw_terms = list(base_terms)
    for term in [*raw_terms, *extra_terms]:
        cleaned = str(term).strip().lower()
        if cleaned and cleaned not in terms:
            terms.append(cleaned)
    return terms


def _weekly_totals(days: list[WeeklyDayRecommendation]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for day in days:
        for key, value in day.result.daily_totals.items():
            totals[key] = totals.get(key, 0.0) + float(value)
    return {key: round(value, 1) for key, value in totals.items()}


def _weekly_variety_counts(days: list[WeeklyDayRecommendation]) -> dict[str, int]:
    return {
        "poultry_days": sum(_day_has_any(day, ("chicken", "turkey", "poultry", "souvlaki")) for day in days),
        "fish_days": sum(_day_has_any(day, ("salmon", "cod", "tuna", "fish", "shrimp", "seafood")) for day in days),
        "legume_days": sum(_day_has_any(day, PLANT_PROTEIN_TERMS) for day in days),
        "vegetable_forward_days": sum(
            any(
                item["food_group"] == "vegetable"
                for meal in day.result.meals
                for item in meal.items
            )
            for day in days
        ),
    }


def _weekly_planner_summary(days: list[WeeklyDayRecommendation]) -> PlanOptimizationSummary:
    if not days:
        return PlanOptimizationSummary(
            planner_mode="hybrid_v2",
            optimized=False,
            substitutions=0,
            portion_adjustments=0,
            remaining_constraints=(),
        )

    summaries = [day.result.planner_summary for day in days]
    notes = []
    for day, summary in zip(days, summaries):
        for note in summary.remaining_constraints:
            day_note = f"{day.day_name}: {note}"
            if day_note not in notes:
                notes.append(day_note)
    return PlanOptimizationSummary(
        planner_mode=summaries[0].planner_mode,
        optimized=any(summary.optimized for summary in summaries),
        substitutions=sum(summary.substitutions for summary in summaries),
        portion_adjustments=sum(summary.portion_adjustments for summary in summaries),
        remaining_constraints=tuple(notes[:8]),
    )


def _day_has_any(day: WeeklyDayRecommendation, terms: tuple[str, ...]) -> bool:
    names = " ".join(
        item["food_name"].lower()
        for meal in day.result.meals
        for item in meal.items
    )
    return any(term in names for term in terms)


def _build_meal(
    catalog: pd.DataFrame,
    profile,
    meal_name: str,
    top_k: int,
    dietary_pattern: str,
    preferences: RecommendationPreferences,
    used_fdc_ids: set[int],
    used_food_keys: set[str],
    data_dir: Path | str | None,
) -> MealRecommendation:
    scored = rank_foods_with_neural_model(
        _foods_for_meal(catalog, meal_name),
        profile,
        meal_name,
        data_dir=str(data_dir) if data_dir is not None else None,
    )
    scored = apply_preferences(scored, preferences, meal_name=meal_name)
    if dietary_pattern == "mediterranean":
        scored = _filter_mediterranean_non_core_foods(scored)
    selected_rows: list[pd.Series] = []
    meal_used_fdc_ids: set[int] = set()

    blueprints = KETO_STYLE_BLUEPRINTS if dietary_pattern == "keto_style" else MEAL_BLUEPRINTS
    for group in blueprints[meal_name][:top_k]:
        group_rows = scored.loc[
            (scored["food_group"] == group)
            & (~scored["fdc_id"].isin(used_fdc_ids))
            & (~scored["fdc_id"].isin(meal_used_fdc_ids))
        ]
        fallback_group_rows = group_rows
        if dietary_pattern in {"mediterranean", "omnivore"}:
            curated_group_rows = group_rows.loc[group_rows.apply(_is_curated_mediterranean, axis=1)]
            if not curated_group_rows.empty:
                group_rows = curated_group_rows
        if (
            dietary_pattern in {"mediterranean", "omnivore", "keto_style"}
            and meal_name in {"Lunch", "Dinner"}
            and group == "protein"
            and not _prefers_plant_protein(preferences)
        ):
            curated_animal_rows = group_rows.loc[
                (~group_rows["vegetarian"]) & group_rows.apply(_is_curated_mediterranean, axis=1)
            ]
            animal_rows = curated_animal_rows
            if animal_rows.empty:
                animal_rows = group_rows.loc[(~group_rows["vegetarian"]) & (group_rows["minimally_processed"])]
            if animal_rows.empty:
                animal_rows = group_rows.loc[~group_rows["vegetarian"]]
            common_rows = animal_rows.loc[animal_rows["food_name"].map(_is_common_omnivore_protein)]
            if not common_rows.empty:
                common_rows = common_rows.loc[
                    ~common_rows["food_name"].map(lambda value: _food_family_key(value) in used_food_keys)
                ]
            if not common_rows.empty:
                animal_rows = common_rows
            if not animal_rows.empty:
                group_rows = animal_rows
        if dietary_pattern == "keto_style":
            group_rows = _prioritize_keto_rows(group_rows, group)
        if group_rows.empty and group == "healthy_fat":
            continue
        if group_rows.empty:
            group_rows = scored.loc[
                (~scored["fdc_id"].isin(used_fdc_ids)) & (~scored["fdc_id"].isin(meal_used_fdc_ids))
        ]
        if not group_rows.empty:
            row = _pick_ranked_row(group_rows, meal_name, selected_rows, profile, used_food_keys, dietary_pattern)
            if row is None and not fallback_group_rows.empty:
                row = _pick_ranked_row(
                    fallback_group_rows,
                    meal_name,
                    selected_rows,
                    profile,
                    used_food_keys,
                    dietary_pattern,
                )
            if row is not None:
                selected_rows.append(row)
                meal_used_fdc_ids.add(int(row["fdc_id"]))

    while len(selected_rows) < min(top_k, 3):
        remaining = scored.loc[(~scored["fdc_id"].isin(used_fdc_ids)) & (~scored["fdc_id"].isin(meal_used_fdc_ids))]
        selected_groups = {str(row.get("food_group", "")) for row in selected_rows}
        remaining = remaining.loc[~remaining["food_group"].isin(selected_groups)]
        if remaining.empty:
            break
        if dietary_pattern == "keto_style":
            remaining = _prioritize_keto_rows(remaining, "")
        row = _pick_ranked_row(remaining, meal_name, selected_rows, profile, used_food_keys, dietary_pattern)
        if row is None:
            break
        selected_rows.append(row)
        meal_used_fdc_ids.add(int(row["fdc_id"]))

    used_fdc_ids.update(meal_used_fdc_ids)
    used_food_keys.update(_food_family_key(row.get("food_name", "")) for row in selected_rows)
    items = [_food_record(row) for row in selected_rows]
    totals = nutrition_totals(items)
    checks = _guidance_checks(items, totals, profile, meal_name, dietary_pattern)
    quality = _quality_score(checks, totals, profile, meal_name)
    return MealRecommendation(
        name=meal_name,
        title=_meal_title(meal_name, items, dietary_pattern),
        items=items,
        totals=totals,
        quality_score=quality,
        model_name=MODEL_NAME,
        guidance_checks=checks,
        explanations=_explanations(items, checks, meal_name, dietary_pattern),
        alternatives=_build_alternatives(scored, selected_rows),
    )


def _pick_ranked_row(
    rows: pd.DataFrame,
    meal_name: str,
    selected_rows: list[pd.Series] | None = None,
    profile=None,
    used_food_keys: set[str] | None = None,
    dietary_pattern: str = "omnivore",
) -> pd.Series | None:
    if selected_rows is not None and profile is not None:
        guardrail_candidates = []
        for _, row in rows.iterrows():
            if _row_fits_meal_guardrails(selected_rows, row, profile, meal_name, used_food_keys or set()):
                guardrail_candidates.append(row)
            if len(guardrail_candidates) >= 40:
                break
        if guardrail_candidates:
            return max(
                guardrail_candidates,
                key=lambda row: _selection_score(row, selected_rows, profile, meal_name, dietary_pattern),
            )
        used_keys = used_food_keys or set()
        selected_keys = {_food_family_key(row.get("food_name", "")) for row in selected_rows}
        for _, row in rows.iterrows():
            candidate_key = _food_family_key(row.get("food_name", ""))
            if (
                candidate_key not in used_keys
                and candidate_key not in selected_keys
                and not _is_low_practicality_standalone(row.get("food_name", ""))
            ):
                if _row_fits_meal_guardrails(selected_rows, row, profile, meal_name, used_keys):
                    return row
        return None
    return rows.iloc[0]


def _selection_score(
    candidate: pd.Series,
    selected_rows: list[pd.Series],
    profile,
    meal_name: str,
    dietary_pattern: str,
) -> float:
    target = meal_target(profile, meal_name)
    totals = _projected_row_totals(selected_rows, candidate)
    score = float(candidate.get("score", 0) or 0)

    score += min(totals["protein_g"] / max(target.protein_g, 1), 1) * 5
    score += min(totals["fiber_g"] / max(target.fiber_g, 1), 1) * 6
    score -= max(0, totals["sodium_mg"] - (target.sodium_mg_limit * 0.75)) / 120
    score -= max(0, totals["saturated_fat_g"] - (target.saturated_fat_g_limit * 0.75)) * 1.5

    if dietary_pattern == "keto_style":
        group = str(candidate.get("food_group", ""))
        fiber_g = float(candidate.get("fiber_g", 0) or 0)
        carbohydrate_g = float(candidate.get("carbohydrate_g", 0) or 0)
        score += fiber_g * (3.4 if group == "vegetable" else 1.5)
        score += float(candidate.get("protein_g", 0) or 0) * (0.18 if group == "protein" else 0.05)
        score += float(candidate.get("fat_g", 0) or 0) * (0.16 if group == "healthy_fat" else 0.04)
        score += 8 if group == "vegetable" and fiber_g >= 3 else 0
        score += 4 if group == "healthy_fat" and fiber_g >= 3 else 0
        score += 5 if totals["fiber_g"] >= target.fiber_g * 0.45 else 0
        score -= max(0, carbohydrate_g - 6) * 0.45
        score -= float(candidate.get("sodium_mg", 0) or 0) / 250
        if _is_common_omnivore_protein(candidate.get("food_name", "")):
            score += 2.5
    if meal_name == "Breakfast":
        score -= float(candidate.get("sodium_mg", 0) or 0) / 120
        score -= float(candidate.get("saturated_fat_g", 0) or 0) * 0.8
    return score


def _row_fits_meal_guardrails(
    selected_rows: list[pd.Series],
    candidate: pd.Series,
    profile,
    meal_name: str,
    used_food_keys: set[str],
) -> bool:
    target = meal_target(profile, meal_name)
    totals = _projected_row_totals(selected_rows, candidate)
    calories = float(candidate.get("calories", 0) or 0)
    group = str(candidate.get("food_group", ""))
    candidate_key = _food_family_key(candidate.get("food_name", ""))
    selected_keys = {_food_family_key(row.get("food_name", "")) for row in selected_rows}

    if candidate_key in used_food_keys or candidate_key in selected_keys:
        return False
    if _is_low_practicality_standalone(candidate.get("food_name", "")):
        return False
    if _overlaps_existing_dish_terms(selected_rows, candidate):
        return False
    if _is_curated_mediterranean(candidate) and group in {"fruit", "vegetable"}:
        calorie_ceiling = target.calories * 1.38
    else:
        calorie_ceiling = target.calories * (1.25 if _is_curated_mediterranean(candidate) else 1.12)
    if totals["calories"] > calorie_ceiling:
        return False
    sugar_fraction = 2.5 if group == "fruit" else 1.8 if _is_curated_mediterranean(candidate) else 1.0
    if totals["sugars_g"] > target.sugars_g_limit * sugar_fraction:
        return False
    sodium_fraction = 1.30 if _is_curated_mediterranean(candidate) else 1.02
    if totals["sodium_mg"] > target.sodium_mg_limit * sodium_fraction:
        return False
    if totals["saturated_fat_g"] > target.saturated_fat_g_limit * 1.05:
        return False
    if group == "vegetable" and selected_rows and calories > 260 and totals["calories"] > target.calories:
        return False
    if group == "healthy_fat" and len(selected_rows) >= 2 and totals["calories"] > target.calories * 1.02:
        return False
    if group == "healthy_fat" and calories > max(140, target.calories * 0.22):
        return False
    breakfast_sugar_fraction = 0.90 if _is_curated_mediterranean(candidate) else 0.45
    if (
        meal_name == "Breakfast"
        and group == "protein"
        and float(candidate.get("sugars_g", 0) or 0) > target.sugars_g_limit * breakfast_sugar_fraction
    ):
        return False
    protein_fraction = 0.75 if _is_curated_mediterranean(candidate) else 0.50
    if group == "protein" and calories > max(320, target.calories * protein_fraction):
        return False
    whole_grain_fraction = 0.60 if _is_curated_mediterranean(candidate) else 0.40
    if group == "whole_grain" and calories > max(280, target.calories * whole_grain_fraction):
        return False
    return True


def _projected_row_totals(selected_rows: list[pd.Series], candidate: pd.Series) -> dict[str, float]:
    keys = ["calories", "protein_g", "carbohydrate_g", "fat_g", "fiber_g", "sugars_g", "sodium_mg", "saturated_fat_g"]
    totals = {key: 0.0 for key in keys}
    for row in [*selected_rows, candidate]:
        for key in keys:
            totals[key] += float(row.get(key, 0) or 0)
    return totals


def _foods_for_meal(catalog: pd.DataFrame, meal_name: str) -> pd.DataFrame:
    tag = meal_name.lower()
    mask = catalog["meal_tags"].str.lower().str.split(",").apply(lambda tags: tag in {t.strip() for t in tags})
    return catalog.loc[mask].reset_index(drop=True)


def _is_common_omnivore_protein(food_name: object) -> bool:
    text = str(food_name).lower()
    return any(term in text for term in COMMON_OMNIVORE_PROTEIN_TERMS)


def _prefers_plant_protein(preferences: RecommendationPreferences) -> bool:
    preferred_terms = preferences.preferred_terms or []
    return any(any(term in preferred for term in PLANT_PROTEIN_TERMS) for preferred in preferred_terms)


def _food_record(row: pd.Series) -> dict[str, Any]:
    record = {
        "fdc_id": int(row["fdc_id"]),
        "food_name": str(row["food_name"]),
        "wweia_category": int(row.get("wweia_category", 0)),
        "wweia_category_description": str(row.get("wweia_category_description", "")),
        "food_group": str(row["food_group"]),
        "meal_tags": str(row["meal_tags"]),
        "serving_grams": float(row["serving_grams"]),
        "calories": float(row["calories"]),
        "protein_g": float(row["protein_g"]),
        "carbohydrate_g": float(row["carbohydrate_g"]),
        "fat_g": float(row["fat_g"]),
        "fiber_g": float(row["fiber_g"]),
        "sugars_g": float(row["sugars_g"]),
        "sodium_mg": float(row["sodium_mg"]),
        "saturated_fat_g": float(row["saturated_fat_g"]),
        "vegetarian": bool(row["vegetarian"]),
        "vegan": bool(row.get("vegan", False)),
        "minimally_processed": bool(row["minimally_processed"]),
        "score": float(row.get("score", 0)),
        "neural_score": float(row.get("neural_score", 0)),
        "source": str(row.get("source", "")),
    }
    record.update(
        {
            "Food_items": record["food_name"],
            "Calories": record["calories"],
            "Fats": record["fat_g"],
            "Proteins": record["protein_g"],
            "Carbohydrates": record["carbohydrate_g"],
            "Fibre": record["fiber_g"],
            "Sugars": record["sugars_g"],
            "VegNovVeg": "0" if record["vegetarian"] else "1",
        }
    )
    return record


def _build_alternatives(scored: pd.DataFrame, selected_rows: list[pd.Series]) -> dict[str, list[dict[str, Any]]]:
    selected_ids = {int(row["fdc_id"]) for row in selected_rows}
    alternatives: dict[str, list[dict[str, Any]]] = {}
    for group in ["protein", "vegetable", "fruit", "whole_grain", "healthy_fat"]:
        rows = scored.loc[(scored["food_group"] == group) & (~scored["fdc_id"].isin(selected_ids))].head(
            ALTERNATIVE_CANDIDATE_POOL
        )
        if not rows.empty:
            alternatives[group] = [_food_record(row) for _, row in rows.iterrows()]
    return alternatives


def _guidance_checks(
    items: list[dict[str, Any]],
    totals: dict[str, float],
    profile,
    meal_name: str,
    dietary_pattern: str,
) -> dict[str, bool]:
    groups = {item["food_group"] for item in items}
    target = meal_target(profile, meal_name)
    return {
        "has_protein": "protein" in groups,
        "has_produce": bool(groups & {"fruit", "vegetable"}),
        "has_high_fiber_food": any(item["fiber_g"] >= 3 for item in items)
        or totals["fiber_g"] >= target.fiber_g * 0.45,
        "sodium_within_meal_limit": totals["sodium_mg"] <= target.sodium_mg_limit,
        "saturated_fat_within_meal_limit": totals["saturated_fat_g"] <= target.saturated_fat_g_limit,
        "sugars_within_meal_limit": _sugars_within_limit(items, totals, target),
        "carbs_within_meal_limit": totals["carbohydrate_g"] <= _carbohydrate_limit(dietary_pattern, meal_name),
        "diverse_food_groups": len(groups) >= 3,
    }


def _quality_score(
    checks: dict[str, bool],
    totals: dict[str, float],
    profile,
    meal_name: str,
) -> float:
    target = meal_target(profile, meal_name)
    score = 46 + sum(6.5 for passed in checks.values() if passed)
    calorie_delta = abs(totals["calories"] - target.calories)
    score -= min(6, (calorie_delta / max(target.calories, 1)) * 6)
    if totals["protein_g"] >= target.protein_g * 0.70:
        score += 4
    if totals["fiber_g"] >= target.fiber_g * 0.45:
        score += 4
    if totals["sodium_mg"] <= target.sodium_mg_limit * 0.70:
        score += 1.5
    if totals["sugars_g"] <= target.sugars_g_limit * 0.65:
        score += 1.5
    return round(max(0, min(99.5, score)), 1)


def _sugars_within_limit(items: list[dict[str, Any]], totals: dict[str, float], target) -> bool:
    if totals["sugars_g"] <= target.sugars_g_limit:
        return True
    fruit_sugars = sum(float(item.get("sugars_g", 0) or 0) for item in items if item.get("food_group") == "fruit")
    return totals["sugars_g"] - fruit_sugars <= target.sugars_g_limit


def _daily_progress(totals: dict[str, float], targets: DailyTargets) -> dict[str, float]:
    return {
        "calories_pct": _pct(totals["calories"], targets.calories),
        "protein_pct": _pct(totals["protein_g"], targets.protein_g),
        "fiber_pct": _pct(totals["fiber_g"], targets.fiber_g),
        "sodium_pct": _pct(totals["sodium_mg"], targets.sodium_mg_limit),
        "saturated_fat_pct": _pct(totals["saturated_fat_g"], targets.saturated_fat_g_limit),
        "sugars_pct": _pct(totals["sugars_g"], targets.sugars_g_limit),
    }


def _macro_percentages(totals: dict[str, float]) -> dict[str, float]:
    protein_kcal = totals["protein_g"] * 4
    carbohydrate_kcal = totals["carbohydrate_g"] * 4
    fat_kcal = totals["fat_g"] * 9
    macro_kcal = protein_kcal + carbohydrate_kcal + fat_kcal
    if macro_kcal <= 0:
        return {"protein_pct": 0.0, "carbohydrate_pct": 0.0, "fat_pct": 0.0}
    return {
        "protein_pct": round((protein_kcal / macro_kcal) * 100, 1),
        "carbohydrate_pct": round((carbohydrate_kcal / macro_kcal) * 100, 1),
        "fat_pct": round((fat_kcal / macro_kcal) * 100, 1),
    }


def _keto_style_catalog(catalog: pd.DataFrame) -> pd.DataFrame:
    allowed_groups = {"protein", "vegetable", "healthy_fat"}
    filtered = catalog.loc[catalog["food_group"].isin(allowed_groups)].copy()
    filtered = filtered.loc[filtered["carbohydrate_g"] <= 18].copy()
    filtered = filtered.loc[filtered["sugars_g"] <= 6].copy()
    filtered = filtered.loc[~filtered["food_name"].str.lower().map(_has_keto_exclusion)].copy()
    return filtered


def _is_curated_mediterranean(row: pd.Series) -> bool:
    return "curated mediterranean" in str(row.get("source", "")).lower()


def _is_low_practicality_standalone(food_name: object) -> bool:
    text = str(food_name).lower()
    return any(term in text for term in LOW_PRACTICALITY_STANDALONE_TERMS)


def _filter_mediterranean_non_core_foods(rows: pd.DataFrame) -> pd.DataFrame:
    filtered = rows.loc[~rows["food_name"].map(_is_mediterranean_non_core_food)].reset_index(drop=True)
    return filtered if not filtered.empty else rows


def _is_mediterranean_non_core_food(food_name: object) -> bool:
    text = str(food_name).lower()
    return any(term in text for term in MEDITERRANEAN_NON_CORE_TERMS)


def _overlaps_existing_dish_terms(selected_rows: list[pd.Series], candidate: pd.Series) -> bool:
    if not selected_rows:
        return False
    candidate_text = str(candidate.get("food_name", "")).lower()
    selected_text = " ".join(str(row.get("food_name", "")).lower() for row in selected_rows)
    repeated_terms = (
        "horta",
        "greek salad",
        "lemon potatoes",
        "brown rice",
        "barley rusk",
        "tomato cucumber",
    )
    return any(term in candidate_text and term in selected_text for term in repeated_terms)


def _prioritize_keto_rows(rows: pd.DataFrame, group: str) -> pd.DataFrame:
    if rows.empty:
        return rows
    ranked = rows.copy()
    group_weight = {
        "vegetable": {"fiber": 3.0, "protein": 0.1, "fat": 0.1, "carb": 0.7},
        "healthy_fat": {"fiber": 2.0, "protein": 0.2, "fat": 0.35, "carb": 0.8},
        "protein": {"fiber": 0.8, "protein": 0.45, "fat": 0.05, "carb": 0.9},
    }.get(group, {"fiber": 1.6, "protein": 0.25, "fat": 0.12, "carb": 0.75})
    ranked["keto_fit_score"] = (
        ranked["score"]
        + ranked["fiber_g"] * group_weight["fiber"]
        + ranked["protein_g"] * group_weight["protein"]
        + ranked["fat_g"] * group_weight["fat"]
        - ranked["carbohydrate_g"] * group_weight["carb"]
        - (ranked["sodium_mg"] / 220)
    )
    if group == "protein":
        ranked.loc[ranked["food_name"].map(_is_common_omnivore_protein), "keto_fit_score"] += 4
    return ranked.sort_values(
        ["keto_fit_score", "score", "fiber_g"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def _has_keto_exclusion(food_name: object) -> bool:
    text = str(food_name).lower()
    return any(term in text for term in KETO_STYLE_EXCLUDE_TERMS)


def _carbohydrate_limit(dietary_pattern: str, meal_name: str) -> float:
    if dietary_pattern != "keto_style":
        return 9999.0
    if meal_name == "Breakfast":
        return 30.0
    return 35.0


def _pct(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return round((value / target) * 100, 1)


def _meal_title(meal_name: str, items: list[dict[str, Any]], dietary_pattern: str) -> str:
    if not items:
        return f"{meal_name} with USDA foods"

    if dietary_pattern == "mediterranean" or _mostly_curated_mediterranean(items):
        names = [_short_food_name(item["food_name"]) for item in items[:3]]
        return f"{meal_name} Mediterranean plate: {', '.join(names)}"

    base = _first_item_name(items, {"whole_grain", "protein"}) or _short_food_name(items[0]["food_name"])
    companions = [_short_food_name(item["food_name"]) for item in items if _short_food_name(item["food_name"]) != base]
    companions = companions[:3]
    if not companions:
        return f"{meal_name} with {base}"
    if len(companions) == 1:
        suffix = companions[0]
    else:
        suffix = ", ".join(companions[:-1]) + f", and {companions[-1]}"
    diet_prefix = "vegan " if dietary_pattern == "vegan" else ""
    return f"{meal_name} {diet_prefix}{base} with {suffix}"


def _first_item_name(items: list[dict[str, Any]], groups: set[str]) -> str | None:
    for item in items:
        if item["food_group"] in groups:
            return _short_food_name(item["food_name"])
    return None


def _short_food_name(food_name: object) -> str:
    text = str(food_name).replace("NFS", "").strip(" ,")
    text = text.split(",")[0].strip()
    return text[:1].lower() + text[1:]


def _mostly_curated_mediterranean(items: list[dict[str, Any]]) -> bool:
    if not items:
        return False
    curated = sum("curated mediterranean" in str(item.get("source", "")).lower() for item in items)
    return curated >= max(2, len(items) // 2)


def _food_family_key(food_name: object) -> str:
    return str(food_name).split(",")[0].strip().lower()


def _explanations(
    items: list[dict[str, Any]],
    checks: dict[str, bool],
    meal_name: str,
    dietary_pattern: str,
) -> list[str]:
    groups = sorted({item["food_group"].replace("_", " ") for item in items})
    explanations = [
        f"{meal_name} combines {', '.join(groups)} for meal-level variety.",
        "Selected from USDA-derived nutrition signals and profile guardrails.",
    ]
    if dietary_pattern == "vegan":
        explanations.append("Vegan mode uses conservative plant-only flags from category and description rules.")
    if checks["has_high_fiber_food"]:
        explanations.append("Includes at least one fiber-rich choice from USDA nutrient data.")
    if checks["sodium_within_meal_limit"]:
        explanations.append("Keeps sodium within the profile's meal-level guardrail.")
    if checks["saturated_fat_within_meal_limit"]:
        explanations.append("Keeps saturated fat within the profile's meal-level guardrail.")
    return explanations


def _health_summary(bmi: BMIResult, profile_goal: str) -> str:
    return f"BMI: {bmi.value:.1f} ({bmi.category_label}). Goal: {profile_goal}."
