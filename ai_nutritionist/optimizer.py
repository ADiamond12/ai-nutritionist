from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ai_nutritionist.profile import DailyTargets
from ai_nutritionist.scoring import MealTarget, nutrition_totals


PORTION_FACTORS = (0.8, 0.9, 1.0, 1.1, 1.2)
MAX_ACCEPTED_ITERATIONS = 16
OBJECTIVE_EPSILON = 1e-7
SCALABLE_KEYS = (
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
NUTRIENT_ALIASES = {
    "calories": "Calories",
    "protein_g": "Proteins",
    "carbohydrate_g": "Carbohydrates",
    "fat_g": "Fats",
    "fiber_g": "Fibre",
    "sugars_g": "Sugars",
}


@dataclass(frozen=True)
class PlanOptimizationSummary:
    planner_mode: str
    optimized: bool
    substitutions: int
    portion_adjustments: int
    remaining_constraints: tuple[str, ...]


@dataclass(frozen=True)
class OptimizableMeal:
    name: str
    items: list[dict[str, Any]]
    alternatives: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class OptimizedMeal:
    name: str
    items: list[dict[str, Any]]


@dataclass(frozen=True)
class PlanOptimizationResult:
    meals: list[OptimizedMeal]
    summary: PlanOptimizationSummary


@dataclass(frozen=True)
class _Coordinate:
    meal_index: int
    item_index: int
    original: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class _PassingLimits:
    daily: tuple[tuple[str, float], ...]
    meals: tuple[tuple[int, str, float], ...]


def optimize_daily_plan(
    meals: Sequence[OptimizableMeal],
    daily_targets: DailyTargets,
    meal_targets: Mapping[str, MealTarget],
    dietary_pattern: str,
    goal_focus: str = "balanced",
) -> PlanOptimizationResult:
    working = _copy_meals(meals)
    coordinates = _build_coordinates(meals)
    initial_objective = plan_objective(working, daily_targets, meal_targets, dietary_pattern, goal_focus)
    current_objective = initial_objective

    for _ in range(MAX_ACCEPTED_ITERATIONS):
        best_objective = current_objective
        best_meals: list[OptimizedMeal] | None = None
        passing_limits = _passing_limits(working, daily_targets, meal_targets, dietary_pattern)
        for coordinate in coordinates:
            for candidate in coordinate.candidates:
                for factor in PORTION_FACTORS:
                    proposed = _replace_coordinate(working, coordinate, _scale_item(candidate, factor))
                    if not _has_unique_foods(proposed) or not _preserves_passing_limits(proposed, passing_limits):
                        continue
                    objective = plan_objective(proposed, daily_targets, meal_targets, dietary_pattern, goal_focus)
                    if objective < best_objective - OBJECTIVE_EPSILON:
                        best_objective = objective
                        best_meals = proposed

        if best_meals is None:
            break
        working = best_meals
        current_objective = best_objective

    substitutions, portion_adjustments = _change_counts(working, coordinates)
    public_meals = [
        OptimizedMeal(name=meal.name, items=[_public_item(item) for item in meal.items])
        for meal in working
    ]
    optimized = current_objective < initial_objective - OBJECTIVE_EPSILON
    return PlanOptimizationResult(
        meals=public_meals,
        summary=PlanOptimizationSummary(
            planner_mode="hybrid_v2",
            optimized=optimized,
            substitutions=substitutions,
            portion_adjustments=portion_adjustments,
            remaining_constraints=_remaining_constraints(public_meals, daily_targets, meal_targets),
        ),
    )


def plan_objective(
    meals: Sequence[OptimizableMeal | OptimizedMeal],
    daily_targets: DailyTargets,
    meal_targets: Mapping[str, MealTarget],
    dietary_pattern: str,
    goal_focus: str = "balanced",
) -> float:
    all_items = [item for meal in meals for item in meal.items]
    daily = nutrition_totals(all_items)
    objective = 0.0

    objective += 30 * _distance(daily["calories"], daily_targets.calories)
    objective += 42 * _shortfall(daily["protein_g"], daily_targets.protein_g)
    objective += 24 * _shortfall(daily["fiber_g"], daily_targets.fiber_g)
    objective += 30 * _excess(daily["sodium_mg"], daily_targets.sodium_mg_limit)
    objective += 24 * _excess(daily["saturated_fat_g"], daily_targets.saturated_fat_g_limit)
    objective += 18 * _excess(daily["sugars_g"], daily_targets.sugars_g_limit)
    objective += _goal_focus_objective(daily, daily_targets, goal_focus)

    for meal in meals:
        totals = nutrition_totals(meal.items)
        target = meal_targets.get(meal.name)
        if target is not None:
            objective += 9 * _distance(totals["calories"], target.calories)
            objective += 12 * _shortfall(totals["protein_g"], target.protein_g)
            objective += 7 * _shortfall(totals["fiber_g"], target.fiber_g)
            objective += 48 * _excess(totals["sodium_mg"], target.sodium_mg_limit)
            objective += 12 * _excess(totals["saturated_fat_g"], target.saturated_fat_g_limit)
            objective += 9 * _excess(_effective_meal_sugars(meal), target.sugars_g_limit)

        groups = {str(item.get("food_group", "")).strip().lower() for item in meal.items}
        objective += 12 if "protein" not in groups else 0
        objective += 10 if not groups.intersection({"fruit", "vegetable"}) else 0
        objective += 5 * max(0, 3 - len(groups))
        if dietary_pattern == "keto_style":
            objective += 24 * _excess(totals["carbohydrate_g"], _keto_carbohydrate_limit(meal.name))

    duplicate_ids, duplicate_families = _duplicate_counts(meals)
    objective += 120 * duplicate_ids
    objective += 100 * duplicate_families
    return round(objective, 8)


def _goal_focus_objective(daily: dict[str, float], targets: DailyTargets, goal_focus: str) -> float:
    if goal_focus == "lower_sodium":
        return 18 * _ratio(daily["sodium_mg"], targets.sodium_mg_limit)
    if goal_focus == "higher_protein":
        return -8 * _ratio(daily["protein_g"], targets.protein_g)
    if goal_focus == "higher_fiber":
        return -8 * _ratio(daily["fiber_g"], targets.fiber_g)
    if goal_focus == "lighter_meals":
        return 24 * _ratio(daily["calories"], targets.calories)
    return 0.0


def _copy_meals(meals: Sequence[OptimizableMeal | OptimizedMeal]) -> list[OptimizedMeal]:
    return [OptimizedMeal(name=meal.name, items=[item.copy() for item in meal.items]) for meal in meals]


def _build_coordinates(meals: Sequence[OptimizableMeal]) -> list[_Coordinate]:
    coordinates = []
    for meal_index, meal in enumerate(meals):
        for item_index, item in enumerate(meal.items):
            group = str(item.get("food_group", "")).strip().lower()
            candidates = [item.copy()]
            seen = {_food_identity(item)}
            for alternative in meal.alternatives.get(group, []):
                if str(alternative.get("food_group", "")).strip().lower() != group:
                    continue
                identity = _food_identity(alternative)
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append(alternative.copy())
            coordinates.append(
                _Coordinate(
                    meal_index=meal_index,
                    item_index=item_index,
                    original=item.copy(),
                    candidates=tuple(candidates),
                )
            )
    return coordinates


def _replace_coordinate(
    meals: Sequence[OptimizedMeal],
    coordinate: _Coordinate,
    replacement: dict[str, Any],
) -> list[OptimizedMeal]:
    proposed = _copy_meals(meals)
    proposed[coordinate.meal_index].items[coordinate.item_index] = replacement
    return proposed


def _scale_item(item: dict[str, Any], factor: float) -> dict[str, Any]:
    scaled = item.copy()
    for key in SCALABLE_KEYS:
        scaled[key] = round(_as_float(item.get(key, 0)) * factor, 1)
    for nutrient, alias in NUTRIENT_ALIASES.items():
        scaled[alias] = scaled[nutrient]
    return scaled


def _has_unique_foods(meals: Sequence[OptimizedMeal]) -> bool:
    duplicate_ids, duplicate_families = _duplicate_counts(meals)
    return duplicate_ids == 0 and duplicate_families == 0


def _passing_limits(
    meals: Sequence[OptimizedMeal],
    daily_targets: DailyTargets,
    meal_targets: Mapping[str, MealTarget],
    dietary_pattern: str,
) -> _PassingLimits:
    daily_totals = nutrition_totals([item for meal in meals for item in meal.items])
    daily_candidates: tuple[tuple[str, float], ...] = (
        ("sodium_mg", daily_targets.sodium_mg_limit),
        ("saturated_fat_g", daily_targets.saturated_fat_g_limit),
        ("sugars_g", daily_targets.sugars_g_limit),
    )
    if dietary_pattern == "keto_style":
        keto_daily_limit = sum(_keto_carbohydrate_limit(meal.name) for meal in meals)
        daily_candidates = (*daily_candidates, ("carbohydrate_g", keto_daily_limit))
    daily = tuple((nutrient, limit) for nutrient, limit in daily_candidates if daily_totals[nutrient] <= limit)

    passing_meals: list[tuple[int, str, float]] = []
    for meal_index, meal in enumerate(meals):
        totals = nutrition_totals(meal.items)
        target = meal_targets.get(meal.name)
        meal_candidates: tuple[tuple[str, float], ...] = ()
        if target is not None:
            meal_candidates = (
                ("sodium_mg", target.sodium_mg_limit),
                ("saturated_fat_g", target.saturated_fat_g_limit),
                ("effective_sugars_g", target.sugars_g_limit),
            )
        if dietary_pattern == "keto_style":
            meal_candidates = (*meal_candidates, ("carbohydrate_g", _keto_carbohydrate_limit(meal.name)))
        passing_meals.extend(
            (meal_index, nutrient, limit)
            for nutrient, limit in meal_candidates
            if _meal_metric(meal, totals, nutrient) <= limit
        )
    return _PassingLimits(daily=daily, meals=tuple(passing_meals))


def _preserves_passing_limits(meals: Sequence[OptimizedMeal], passing_limits: _PassingLimits) -> bool:
    daily_totals = nutrition_totals([item for meal in meals for item in meal.items])
    if any(daily_totals[nutrient] > limit for nutrient, limit in passing_limits.daily):
        return False
    meal_totals = [nutrition_totals(meal.items) for meal in meals]
    return not any(
        _meal_metric(meals[index], meal_totals[index], nutrient) > limit
        for index, nutrient, limit in passing_limits.meals
    )


def _meal_metric(meal: OptimizedMeal, totals: dict[str, float], nutrient: str) -> float:
    if nutrient == "effective_sugars_g":
        return _effective_meal_sugars(meal)
    return totals[nutrient]


def _effective_meal_sugars(meal: OptimizableMeal | OptimizedMeal) -> float:
    totals = nutrition_totals(meal.items)
    fruit_sugars = sum(
        _as_float(item.get("sugars_g", 0))
        for item in meal.items
        if item.get("food_group") == "fruit"
    )
    return max(0.0, totals["sugars_g"] - fruit_sugars)


def _duplicate_counts(meals: Sequence[OptimizableMeal | OptimizedMeal]) -> tuple[int, int]:
    ids: list[str] = []
    families: list[str] = []
    for meal in meals:
        for item in meal.items:
            fdc_id = str(item.get("fdc_id", "")).strip()
            family = _food_family(item)
            if fdc_id:
                ids.append(fdc_id)
            if family:
                families.append(family)
    return len(ids) - len(set(ids)), len(families) - len(set(families))


def _food_identity(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get("fdc_id", "")).strip(), _food_family(item)


def _food_family(item: dict[str, Any]) -> str:
    explicit_family = str(item.get("food_family", "")).strip().lower()
    if explicit_family:
        return explicit_family
    return str(item.get("food_name", "")).split(",")[0].strip().lower()


def _change_counts(meals: Sequence[OptimizedMeal], coordinates: Sequence[_Coordinate]) -> tuple[int, int]:
    substitutions = 0
    portion_adjustments = 0
    for coordinate in coordinates:
        item = meals[coordinate.meal_index].items[coordinate.item_index]
        substitutions += _food_identity(item) != _food_identity(coordinate.original)
        base_candidate = next(
            (candidate for candidate in coordinate.candidates if _food_identity(candidate) == _food_identity(item)),
            coordinate.original,
        )
        base_serving = _as_float(base_candidate.get("serving_grams", 0))
        serving = _as_float(item.get("serving_grams", 0))
        portion_adjustments += abs(serving - base_serving) > OBJECTIVE_EPSILON
    return substitutions, portion_adjustments


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_optimizer_")}


def _remaining_constraints(
    meals: Sequence[OptimizedMeal],
    daily_targets: DailyTargets,
    meal_targets: Mapping[str, MealTarget],
) -> tuple[str, ...]:
    totals = nutrition_totals([item for meal in meals for item in meal.items])
    notes: list[str] = []
    if daily_targets.calories > 0 and not 0.85 <= totals["calories"] / daily_targets.calories <= 1.15:
        notes.append("Daily calories are outside 15% of target.")
    if daily_targets.protein_g > 0 and totals["protein_g"] < daily_targets.protein_g * 0.8:
        notes.append("Daily protein is below 80% of target.")
    if daily_targets.fiber_g > 0 and totals["fiber_g"] < daily_targets.fiber_g * 0.7:
        notes.append("Daily fiber is below 70% of target.")
    if totals["sodium_mg"] > daily_targets.sodium_mg_limit:
        notes.append("Daily sodium exceeds its limit.")
    if totals["saturated_fat_g"] > daily_targets.saturated_fat_g_limit:
        notes.append("Daily saturated fat exceeds its limit.")
    if totals["sugars_g"] > daily_targets.sugars_g_limit:
        notes.append("Daily sugars exceed their limit.")

    sodium_excesses = sum(
        nutrition_totals(meal.items)["sodium_mg"] > target.sodium_mg_limit
        for meal in meals
        if (target := meal_targets.get(meal.name)) is not None
    )
    if sodium_excesses:
        label = "meal" if sodium_excesses == 1 else "meals"
        verb = "exceeds" if sodium_excesses == 1 else "exceed"
        notes.append(f"{sodium_excesses} {label} {verb} meal sodium limits.")
    return tuple(notes)


def _distance(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return abs(value - target) / target


def _ratio(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return value / target


def _shortfall(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return max(0.0, target - value) / target


def _excess(value: float, limit: float) -> float:
    if limit <= 0:
        return 0.0
    return max(0.0, value - limit) / limit


def _keto_carbohydrate_limit(meal_name: str) -> float:
    return 30.0 if meal_name == "Breakfast" else 35.0


def _as_float(value: object) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value)  # type: ignore[arg-type]
