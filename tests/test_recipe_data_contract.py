from pathlib import Path

import pandas as pd
import pytest

from ai_nutritionist.constants import CATALOG_COLUMNS
from ai_nutritionist.data import load_food_catalog
from ai_nutritionist.plan_outputs import build_recipe_ingredient_grocery_list_for_plan
from ai_nutritionist.recommender import recommend
from ai_nutritionist.recipes import (
    RecipeDataError,
    aggregate_recipe_nutrition,
    build_recipe_ingredient_grocery_list,
    build_recipe_ingredient_grocery_list_from_items,
    load_recipe_tables,
    project_recipes_to_catalog,
    recipe_ingredient_grocery_csv,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "recipes"


def test_recipe_fixture_tables_project_to_existing_catalog_contract():
    tables = load_recipe_tables(FIXTURE_DIR)

    projected = project_recipes_to_catalog(tables)

    assert list(projected.columns) == CATALOG_COLUMNS
    assert len(projected) == 3
    assert set(projected["food_name"]) == {
        "Fixture Lentil Soup",
        "Fixture Greek Yogurt Bowl",
        "Fixture Chicken Rice Plate",
    }
    assert projected["fdc_id"].is_unique
    assert (projected["serving_grams"] > 0).all()
    assert projected["source"].str.contains("Recipe contract fixture").all()


def test_recipe_aggregation_is_deterministic_and_derives_dietary_and_allergen_fields():
    tables = load_recipe_tables(FIXTURE_DIR)

    nutrition = aggregate_recipe_nutrition(tables)

    lentil = nutrition.set_index("recipe_id").loc["fixture_lentil_soup_v1"]
    assert lentil["calories"] == pytest.approx(246.3)
    assert lentil["sodium_mg"] == pytest.approx(422.1)
    assert lentil["vegetarian"] is True
    assert lentil["vegan"] is True
    assert lentil["allergen_tags"] == ""

    yogurt = nutrition.set_index("recipe_id").loc["fixture_greek_yogurt_bowl_v1"]
    assert yogurt["vegetarian"] is True
    assert yogurt["vegan"] is False
    assert yogurt["allergen_tags"] == "milk,tree_nut"

    chicken = nutrition.set_index("recipe_id").loc["fixture_chicken_rice_plate_v1"]
    assert chicken["vegetarian"] is False
    assert chicken["vegan"] is False


def test_recipe_validation_rejects_missing_required_nutrient_values(tmp_path):
    for filename in ["recipes.csv", "recipe_sources.csv", "recipe_ingredients.csv"]:
        source = FIXTURE_DIR / filename
        target = tmp_path / filename
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    ingredients_path = tmp_path / "recipe_ingredients.csv"
    ingredients = pd.read_csv(ingredients_path)
    ingredients.loc[0, "sodium_mg_per_100g"] = None
    ingredients.to_csv(ingredients_path, index=False)

    with pytest.raises(RecipeDataError, match="missing required nutrient"):
        load_recipe_tables(tmp_path)


def test_recipe_ingredient_grocery_list_groups_ingredients_without_public_scores():
    tables = load_recipe_tables(FIXTURE_DIR)

    grocery = build_recipe_ingredient_grocery_list(
        tables,
        [
            {"recipe_id": "fixture_lentil_soup_v1", "servings": 2},
            {"recipe_id": "fixture_greek_yogurt_bowl_v1", "servings": 1},
        ],
    )
    csv_text = recipe_ingredient_grocery_csv(grocery)

    lentils = next(item for item in grocery if item["ingredient_name"] == "lentils")
    assert lentils["edible_grams"] == pytest.approx(200.0)
    assert lentils["recipe_count"] == 1
    assert lentils["calories"] == pytest.approx(232.0)

    olive_oil = next(item for item in grocery if item["ingredient_name"] == "olive oil")
    assert olive_oil["edible_grams"] == pytest.approx(20.0)

    walnuts = next(item for item in grocery if item["ingredient_name"] == "walnuts")
    assert walnuts["allergen_tags"] == "tree_nut"
    assert "score" not in walnuts
    assert "neural_score" not in walnuts
    assert "ingredient_role,ingredient_name,edible_grams,recipe_count" in csv_text


def test_default_catalog_includes_reviewed_recipe_projection_without_internal_metadata():
    catalog = load_food_catalog()

    recipe_rows = catalog.loc[catalog["source"].str.contains("Recipe contract curated_estimate")]

    assert list(catalog.columns) == CATALOG_COLUMNS
    assert len(recipe_rows) >= 9
    assert "recipe_id" not in catalog.columns
    assert "recipe_version" not in catalog.columns
    assert "recipe_allergen_tags" not in catalog.columns
    assert "Chicken souvlaki plate with Greek salad and pita" in set(recipe_rows["food_name"])
    assert "Fasolada bean soup with tomato carrot and olive oil" in set(recipe_rows["food_name"])


def test_runtime_recipe_pilot_adds_practical_greek_coverage_and_grocery_expansion():
    tables = load_recipe_tables(Path(__file__).resolve().parents[1] / "data" / "recipes")
    projected = project_recipes_to_catalog(tables, include_metadata=True, statuses={"reviewed"})
    by_name = projected.set_index("food_name")

    assert len(projected) >= 9
    assert bool(by_name.loc["Fasolada bean soup with tomato carrot and olive oil", "vegan"]) is True
    assert bool(by_name.loc["Gigantes beans with briam-style roasted vegetables", "vegan"]) is True
    assert bool(by_name.loc["Cod plaki with tomato onion potatoes and herbs", "vegan"]) is False
    assert bool(by_name.loc["Shrimp tomato orzo with spinach and feta", "vegetarian"]) is False

    grocery = build_recipe_ingredient_grocery_list_from_items(
        tables,
        [
            by_name.loc["Fasolada bean soup with tomato carrot and olive oil"].to_dict(),
            by_name.loc["Cod plaki with tomato onion potatoes and herbs"].to_dict(),
        ],
    )

    ingredient_names = {item["ingredient_name"] for item in grocery}
    assert {"white beans", "cod", "olive oil", "crushed tomato"}.issubset(ingredient_names)
    assert all("recipe_id" not in item for item in grocery)
    assert all("neural_score" not in item for item in grocery)


def test_recipe_grocery_can_be_built_from_projected_catalog_items_without_recipe_ids():
    tables = load_recipe_tables(FIXTURE_DIR)
    projected = project_recipes_to_catalog(tables)
    public_items = [
        projected.loc[projected["food_name"] == "Fixture Lentil Soup"].iloc[0].to_dict(),
        projected.loc[projected["food_name"] == "Fixture Greek Yogurt Bowl"].iloc[0].to_dict(),
    ]

    grocery = build_recipe_ingredient_grocery_list_from_items(tables, public_items)

    assert grocery
    assert any(item["ingredient_name"] == "lentils" for item in grocery)
    assert any(item["ingredient_name"] == "walnuts" for item in grocery)
    assert all("recipe_id" not in item for item in grocery)
    assert all("score" not in item for item in grocery)


def test_recipe_backed_rows_are_reachable_with_explicit_preferences():
    result = recommend(
        weight_kg=75,
        height_cm=180,
        age=30,
        sex="male",
        dietary_pattern="mediterranean",
        preferred_terms="yogurt oat",
        top_k=4,
    )

    recipe_items = [
        item
        for meal in result.meals
        for item in meal.items
        if "Recipe contract curated_estimate" in item["source"]
    ]
    ingredient_grocery = build_recipe_ingredient_grocery_list_for_plan(result)

    assert recipe_items
    assert ingredient_grocery
    assert any(item["ingredient_name"] == "Greek yogurt" for item in ingredient_grocery)
