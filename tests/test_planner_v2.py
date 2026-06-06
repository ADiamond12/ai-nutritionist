from dataclasses import FrozenInstanceError

import pytest

from ai_nutritionist.optimizer import OptimizableMeal, optimize_daily_plan, plan_objective
from ai_nutritionist.profile import DailyTargets
from ai_nutritionist.scoring import MealTarget, nutrition_totals


NUTRIENT_ALIASES = {
    "calories": "Calories",
    "protein_g": "Proteins",
    "carbohydrate_g": "Carbohydrates",
    "fat_g": "Fats",
    "fiber_g": "Fibre",
    "sugars_g": "Sugars",
}


def _food(
    fdc_id: int,
    name: str,
    group: str,
    *,
    serving_grams: float = 100,
    calories: float = 300,
    protein_g: float = 20,
    carbohydrate_g: float = 25,
    fat_g: float = 10,
    fiber_g: float = 5,
    sugars_g: float = 4,
    sodium_mg: float = 300,
    saturated_fat_g: float = 2,
    **extra: object,
) -> dict[str, object]:
    item = {
        "fdc_id": fdc_id,
        "food_name": name,
        "food_group": group,
        "serving_grams": serving_grams,
        "calories": calories,
        "protein_g": protein_g,
        "carbohydrate_g": carbohydrate_g,
        "fat_g": fat_g,
        "fiber_g": fiber_g,
        "sugars_g": sugars_g,
        "sodium_mg": sodium_mg,
        "saturated_fat_g": saturated_fat_g,
        "source": "synthetic",
        **extra,
    }
    for nutrient, alias in NUTRIENT_ALIASES.items():
        item[alias] = item[nutrient]
    return item


@pytest.fixture
def targets() -> tuple[DailyTargets, dict[str, MealTarget]]:
    daily = DailyTargets(
        calories=1800,
        protein_g=100,
        fiber_g=30,
        sodium_mg_limit=2300,
        saturated_fat_g_limit=20,
        sugars_g_limit=50,
    )
    meal = MealTarget(
        calories=600,
        protein_g=33,
        fiber_g=10,
        sodium_mg_limit=700,
        saturated_fat_g_limit=7,
        sugars_g_limit=18,
    )
    return daily, {"Breakfast": meal, "Lunch": meal, "Dinner": meal}


def _balanced_meals() -> list[OptimizableMeal]:
    return [
        OptimizableMeal(
            name="Breakfast",
            items=[
                _food(1, "Greek yogurt", "protein", calories=320, protein_g=28, sodium_mg=180),
                _food(2, "Blueberries", "fruit", calories=140, protein_g=2, fiber_g=7, sodium_mg=5),
                _food(3, "Oats", "whole_grain", calories=260, protein_g=9, fiber_g=6, sodium_mg=10),
            ],
            alternatives={},
        ),
        OptimizableMeal(
            name="Lunch",
            items=[
                _food(4, "Chicken breast", "protein", calories=340, protein_g=45, sodium_mg=250),
                _food(5, "Broccoli", "vegetable", calories=120, protein_g=5, fiber_g=8, sodium_mg=50),
                _food(6, "Brown rice", "whole_grain", calories=260, protein_g=6, fiber_g=4, sodium_mg=10),
            ],
            alternatives={},
        ),
        OptimizableMeal(
            name="Dinner",
            items=[
                _food(7, "Salmon", "protein", calories=350, protein_g=40, sodium_mg=220),
                _food(8, "Spinach", "vegetable", calories=100, protein_g=5, fiber_g=7, sodium_mg=70),
                _food(9, "Quinoa", "whole_grain", calories=260, protein_g=8, fiber_g=5, sodium_mg=15),
            ],
            alternatives={},
        ),
    ]


def test_optimizer_is_deterministic_and_returns_frozen_summary(targets):
    daily_targets, meal_targets = targets
    meals = _balanced_meals()

    first = optimize_daily_plan(meals, daily_targets, meal_targets, "omnivore")
    second = optimize_daily_plan(meals, daily_targets, meal_targets, "omnivore")

    assert first == second
    assert first.summary.planner_mode == "hybrid_v2"
    with pytest.raises(FrozenInstanceError):
        first.summary.optimized = False  # type: ignore[misc]


def test_optimizer_never_increases_objective(targets):
    daily_targets, meal_targets = targets
    meals = _balanced_meals()

    before = plan_objective(meals, daily_targets, meal_targets, "omnivore")
    result = optimize_daily_plan(meals, daily_targets, meal_targets, "omnivore")
    after = plan_objective(result.meals, daily_targets, meal_targets, "omnivore")

    assert after <= before


def test_keto_optimization_preserves_passing_saturated_fat_limits():
    daily_targets = DailyTargets(
        calories=1320,
        protein_g=20,
        fiber_g=5,
        sodium_mg_limit=2300,
        saturated_fat_g_limit=10,
        sugars_g_limit=50,
    )
    meal_targets = {
        "Dinner": MealTarget(
            calories=1320,
            protein_g=20,
            fiber_g=5,
            sodium_mg_limit=2300,
            saturated_fat_g_limit=10,
            sugars_g_limit=50,
        )
    }
    meal = OptimizableMeal(
        name="Dinner",
        items=[
            _food(
                50,
                "Keto protein",
                "protein",
                calories=900,
                protein_g=30,
                carbohydrate_g=1,
                fiber_g=0,
                saturated_fat_g=9.5,
                sodium_mg=10,
                sugars_g=0,
            ),
            _food(
                51,
                "Keto greens",
                "vegetable",
                calories=100,
                carbohydrate_g=5,
                fiber_g=5,
                saturated_fat_g=0,
                sodium_mg=10,
                sugars_g=0,
            ),
            _food(
                52,
                "Keto avocado",
                "healthy_fat",
                calories=100,
                carbohydrate_g=5,
                fiber_g=5,
                saturated_fat_g=0,
                sodium_mg=10,
                sugars_g=0,
            ),
        ],
        alternatives={},
    )
    before = nutrition_totals(meal.items)

    result = optimize_daily_plan([meal], daily_targets, meal_targets, "keto_style")
    after = nutrition_totals(result.meals[0].items)

    assert before["saturated_fat_g"] <= daily_targets.saturated_fat_g_limit
    assert before["saturated_fat_g"] <= meal_targets["Dinner"].saturated_fat_g_limit
    assert after["saturated_fat_g"] <= daily_targets.saturated_fat_g_limit
    assert after["saturated_fat_g"] <= meal_targets["Dinner"].saturated_fat_g_limit


@pytest.mark.parametrize(
    ("nutrient", "dietary_pattern", "passing_value", "limit"),
    [
        ("sodium_mg", "omnivore", 95, 100),
        ("sugars_g", "omnivore", 9.5, 10),
        ("carbohydrate_g", "keto_style", 33, 35),
    ],
)
def test_optimizer_preserves_other_passing_hard_limits(nutrient, dietary_pattern, passing_value, limit):
    daily_targets = DailyTargets(
        calories=1300,
        protein_g=20,
        fiber_g=5,
        sodium_mg_limit=limit if nutrient == "sodium_mg" else 2300,
        saturated_fat_g_limit=20,
        sugars_g_limit=limit if nutrient == "sugars_g" else 50,
    )
    meal_targets = {
        "Dinner": MealTarget(
            calories=1300,
            protein_g=20,
            fiber_g=5,
            sodium_mg_limit=limit if nutrient == "sodium_mg" else 2300,
            saturated_fat_g_limit=20,
            sugars_g_limit=limit if nutrient == "sugars_g" else 50,
        )
    }
    constrained_item = {
        "sodium_mg": 0,
        "sugars_g": 0,
        "carbohydrate_g": 0,
        nutrient: passing_value,
    }
    meal = OptimizableMeal(
        name="Dinner",
        items=[
            _food(60, "Constrained protein", "protein", calories=1000, **constrained_item),
            _food(
                61,
                "Constraint greens",
                "vegetable",
                calories=50,
                carbohydrate_g=0,
                sodium_mg=0,
                sugars_g=0,
            ),
            _food(
                62,
                "Constraint avocado",
                "healthy_fat",
                calories=50,
                carbohydrate_g=0,
                sodium_mg=0,
                sugars_g=0,
            ),
        ],
        alternatives={},
    )

    result = optimize_daily_plan([meal], daily_targets, meal_targets, dietary_pattern)
    after = nutrition_totals(result.meals[0].items)

    assert after[nutrient] <= limit


def test_optimizer_preserves_fruit_aware_meal_sugar_guardrail():
    daily_targets = DailyTargets(
        calories=1300,
        protein_g=20,
        fiber_g=5,
        sodium_mg_limit=2300,
        saturated_fat_g_limit=20,
        sugars_g_limit=80,
    )
    meal_targets = {
        "Breakfast": MealTarget(
            calories=1300,
            protein_g=20,
            fiber_g=5,
            sodium_mg_limit=2300,
            saturated_fat_g_limit=20,
            sugars_g_limit=10,
        )
    }
    meal = OptimizableMeal(
        name="Breakfast",
        items=[
            _food(70, "Sweet oats", "whole_grain", calories=800, sugars_g=9),
            _food(71, "Soy milk", "protein", calories=100, sugars_g=0),
            _food(72, "Whole fruit", "fruit", calories=100, sugars_g=20),
        ],
        alternatives={},
    )

    result = optimize_daily_plan([meal], daily_targets, meal_targets, "vegan")
    non_fruit_sugars = sum(
        item["sugars_g"]
        for item in result.meals[0].items
        if item["food_group"] != "fruit"
    )

    assert non_fruit_sugars <= meal_targets["Breakfast"].sugars_g_limit


def test_lower_sodium_focus_prefers_lower_sodium_option_below_hard_limit(targets):
    daily_targets, meal_targets = targets
    meal = OptimizableMeal(
        name="Lunch",
        items=[
            _food(80, "Higher sodium protein", "protein", sodium_mg=500),
            _food(81, "Lunch greens", "vegetable", sodium_mg=50),
            _food(82, "Lunch grain", "whole_grain", sodium_mg=50),
        ],
        alternatives={
            "protein": [
                _food(83, "Lower sodium protein", "protein", sodium_mg=100),
            ]
        },
    )

    result = optimize_daily_plan([meal], daily_targets, meal_targets, "omnivore", "lower_sodium")

    assert result.meals[0].items[0]["fdc_id"] == 83


def test_optimizer_uses_lower_sodium_same_group_alternative(targets):
    daily_targets, meal_targets = targets
    salty = _food(10, "Salty chicken", "protein", sodium_mg=2600, calories=500, protein_g=45)
    lower_sodium = _food(11, "Plain chicken", "protein", sodium_mg=120, calories=500, protein_g=45)
    meal = OptimizableMeal(
        name="Lunch",
        items=[
            salty,
            _food(12, "Lunch tomato", "vegetable", calories=60, sodium_mg=10),
            _food(13, "Lunch barley", "whole_grain", calories=180, sodium_mg=10),
        ],
        alternatives={"protein": [lower_sodium]},
    )

    before = plan_objective([meal], daily_targets, meal_targets, "omnivore")
    result = optimize_daily_plan([meal], daily_targets, meal_targets, "omnivore")
    after = plan_objective(result.meals, daily_targets, meal_targets, "omnivore")

    assert after < before
    assert result.meals[0].items[0]["fdc_id"] == 11
    assert result.meals[0].items[0]["food_group"] == "protein"
    assert result.summary.substitutions == 1


def test_portions_are_bounded_and_aliases_stay_synchronized(targets):
    daily_targets, meal_targets = targets
    meal = OptimizableMeal(
        name="Breakfast",
        items=[
            _food(20, "Eggs", "protein", serving_grams=120, calories=900, sodium_mg=100),
            _food(21, "Breakfast pepper", "vegetable", serving_grams=80, calories=300, sodium_mg=10),
            _food(22, "Breakfast oats", "whole_grain", serving_grams=50, calories=700, sodium_mg=10),
        ],
        alternatives={},
    )
    original_servings = {item["fdc_id"]: item["serving_grams"] for item in meal.items}

    result = optimize_daily_plan([meal], daily_targets, meal_targets, "omnivore")

    assert result.summary.portion_adjustments > 0
    for item in result.meals[0].items:
        original = original_servings[item["fdc_id"]]
        assert original * 0.8 <= item["serving_grams"] <= original * 1.2
        for nutrient, alias in NUTRIENT_ALIASES.items():
            assert item[alias] == item[nutrient]


def test_substitutions_preserve_groups_and_never_create_duplicates(targets):
    daily_targets, meal_targets = targets
    meals = _balanced_meals()
    meals[1].alternatives["protein"] = [
        _food(1, "Greek yogurt, plain", "protein", sodium_mg=1),
        _food(30, "Low sodium lentils", "protein", sodium_mg=1, protein_g=45),
        _food(31, "Wrong group candidate", "vegetable", sodium_mg=0, protein_g=45),
    ]
    original_groups = [[item["food_group"] for item in meal.items] for meal in meals]

    result = optimize_daily_plan(meals, daily_targets, meal_targets, "omnivore")
    result_items = [item for meal in result.meals for item in meal.items]
    families = [str(item["food_name"]).split(",")[0].strip().lower() for item in result_items]

    assert [[item["food_group"] for item in meal.items] for meal in result.meals] == original_groups
    assert len({item["fdc_id"] for item in result_items}) == len(result_items)
    assert len(set(families)) == len(families)


def test_result_strips_optimizer_internal_fields_and_reports_constraints(targets):
    daily_targets, meal_targets = targets
    item = _food(
        40,
        "Internal field food",
        "protein",
        calories=100,
        protein_g=5,
        fiber_g=1,
        sodium_mg=2500,
        saturated_fat_g=30,
        sugars_g=80,
        _optimizer_objective=99,
        _optimizer_base_serving_grams=100,
    )
    meal = OptimizableMeal(name="Lunch", items=[item], alternatives={})

    result = optimize_daily_plan([meal], daily_targets, meal_targets, "omnivore")
    result_item = result.meals[0].items[0]

    assert not any(key.startswith("_optimizer_") for key in result_item)
    assert any("calorie" in note.lower() and "15%" in note for note in result.summary.remaining_constraints)
    assert any("protein" in note.lower() and "80%" in note for note in result.summary.remaining_constraints)
    assert any("fiber" in note.lower() and "70%" in note for note in result.summary.remaining_constraints)
    assert any("sodium" in note.lower() for note in result.summary.remaining_constraints)
    assert any("saturated fat" in note.lower() for note in result.summary.remaining_constraints)
    assert any("sugars" in note.lower() for note in result.summary.remaining_constraints)
    assert any("meal" in note.lower() and "sodium" in note.lower() for note in result.summary.remaining_constraints)
