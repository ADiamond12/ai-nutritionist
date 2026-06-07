from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from io import StringIO
from pathlib import Path
from typing import Any
import csv

import pandas as pd

from ai_nutritionist.constants import CATALOG_COLUMNS


RECIPE_FILENAME = "recipes.csv"
INGREDIENT_FILENAME = "recipe_ingredients.csv"
SOURCE_FILENAME = "recipe_sources.csv"
RECIPE_DATA_DIRNAME = "recipes"

NUTRIENT_COLUMNS = (
    "calories",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sugars_g",
    "sodium_mg",
    "saturated_fat_g",
)
NUTRIENT_PER_100G_COLUMNS = tuple(f"{column}_per_100g" for column in NUTRIENT_COLUMNS)

RECIPE_COLUMNS = (
    "recipe_id",
    "recipe_name",
    "description",
    "recipe_version",
    "status",
    "meal_tags",
    "cuisine_tags",
    "dietary_pattern_tags",
    "food_group_primary",
    "servings_per_recipe",
    "serving_grams",
    "yield_grams",
    "yield_basis",
    "prep_time_minutes",
    "cook_time_minutes",
    "cooking_method",
    "default_portion_servings",
    "portion_min_servings",
    "portion_max_servings",
    "allergen_tags",
    "allergen_review_status",
    "dietary_review_status",
    "nutrition_review_status",
    "source_id",
    "notes",
)
INGREDIENT_COLUMNS = (
    "recipe_id",
    "ingredient_id",
    "ingredient_name",
    "ingredient_role",
    "fdc_id",
    "fdc_data_type",
    "source_food_name",
    "quantity",
    "unit",
    "edible_grams",
    "preparation_state",
    "nutrient_basis",
    "is_optional",
    "substitution_group",
    "vegetarian",
    "vegan",
    "contains_allergen_tags",
    "mapping_confidence",
    "mapping_notes",
    *NUTRIENT_PER_100G_COLUMNS,
)
SOURCE_COLUMNS = (
    "source_id",
    "source_type",
    "source_title",
    "source_url",
    "source_release",
    "source_license",
    "created_by",
    "created_at",
    "reviewed_at",
    "review_notes",
)

ALLOWED_FOOD_GROUPS = {"protein", "vegetable", "fruit", "whole_grain", "healthy_fat"}
ALLOWED_INGREDIENT_ROLES = {
    "protein",
    "vegetable",
    "fruit",
    "whole_grain",
    "healthy_fat",
    "seasoning",
    "liquid",
    "other",
}
ALLOWED_STATUSES = {"fixture", "draft", "reviewed", "retired"}
PRODUCTION_STATUSES = {"fixture", "reviewed"}


class RecipeDataError(ValueError):
    """Raised when recipe contract files are missing or invalid."""


@dataclass(frozen=True)
class RecipeTables:
    recipes: pd.DataFrame
    ingredients: pd.DataFrame
    sources: pd.DataFrame


def load_recipe_tables(recipe_dir: Path | str) -> RecipeTables:
    base = Path(recipe_dir)
    recipes = _read_contract_csv(base / RECIPE_FILENAME, RECIPE_COLUMNS)
    ingredients = _read_contract_csv(base / INGREDIENT_FILENAME, INGREDIENT_COLUMNS)
    sources = _read_contract_csv(base / SOURCE_FILENAME, SOURCE_COLUMNS)

    recipes = _normalize_recipes(recipes)
    ingredients = _normalize_ingredients(ingredients)
    sources = _normalize_sources(sources)
    tables = RecipeTables(recipes=recipes, ingredients=ingredients, sources=sources)
    _validate_tables(tables)
    return tables


def aggregate_recipe_nutrition(tables: RecipeTables) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source_by_id = tables.sources.set_index("source_id").to_dict("index")
    for _, recipe in tables.recipes.iterrows():
        recipe_id = str(recipe["recipe_id"])
        ingredients = tables.ingredients.loc[
            (tables.ingredients["recipe_id"] == recipe_id) & (~tables.ingredients["is_optional"])
        ]
        servings = float(recipe["servings_per_recipe"])
        total_grams = float(ingredients["edible_grams"].sum())
        yield_grams = float(recipe.get("yield_grams", 0) or 0)
        serving_grams = yield_grams / servings if yield_grams > 0 else total_grams / servings

        nutrient_totals = {}
        for nutrient, source_column in zip(NUTRIENT_COLUMNS, NUTRIENT_PER_100G_COLUMNS):
            total = float((ingredients[source_column] * ingredients["edible_grams"] / 100).sum())
            nutrient_totals[nutrient] = round(total / servings, 1)

        allergen_tags = _join_tags(
            [
                *recipe.get("allergen_tags_list", []),
                *(tag for tags in ingredients["contains_allergen_tags_list"] for tag in tags),
            ]
        )
        source = source_by_id.get(str(recipe["source_id"]), {})
        rows.append(
            {
                "recipe_id": recipe_id,
                "recipe_name": str(recipe["recipe_name"]),
                "recipe_version": str(recipe["recipe_version"]),
                "status": str(recipe["status"]),
                "meal_tags": str(recipe["meal_tags"]),
                "food_group_primary": str(recipe["food_group_primary"]),
                "servings_per_recipe": servings,
                "serving_grams": round(serving_grams, 1),
                "vegetarian": bool(ingredients["vegetarian"].all()),
                "vegan": bool(ingredients["vegan"].all()),
                "allergen_tags": allergen_tags,
                "source_id": str(recipe["source_id"]),
                "source_title": str(source.get("source_title", "")),
                "source_type": str(source.get("source_type", "")),
                **nutrient_totals,
            }
        )

    result = pd.DataFrame(rows)
    for column in ["vegetarian", "vegan"]:
        result[column] = result[column].map(bool).astype(object)
    return result


def project_recipes_to_catalog(
    tables: RecipeTables,
    *,
    include_metadata: bool = False,
    statuses: set[str] | None = None,
) -> pd.DataFrame:
    allowed_statuses = statuses or PRODUCTION_STATUSES
    nutrition = aggregate_recipe_nutrition(tables)
    nutrition = nutrition.loc[nutrition["status"].isin(allowed_statuses)].copy()

    rows = []
    for _, row in nutrition.iterrows():
        catalog_row: dict[str, Any] = {
            "fdc_id": _stable_recipe_fdc_id(str(row["recipe_id"])),
            "food_name": row["recipe_name"],
            "wweia_category": 9901,
            "wweia_category_description": "Curated ingredient-level recipe",
            "food_group": row["food_group_primary"],
            "meal_tags": row["meal_tags"],
            "serving_grams": row["serving_grams"],
            "calories": row["calories"],
            "protein_g": row["protein_g"],
            "carbohydrate_g": row["carbohydrate_g"],
            "fat_g": row["fat_g"],
            "fiber_g": row["fiber_g"],
            "sugars_g": row["sugars_g"],
            "sodium_mg": row["sodium_mg"],
            "saturated_fat_g": row["saturated_fat_g"],
            "vegetarian": bool(row["vegetarian"]),
            "vegan": bool(row["vegan"]),
            "minimally_processed": False,
            "source": f"Recipe contract {row['source_type']}: {row['source_title']}".strip(),
        }
        if include_metadata:
            catalog_row.update(
                {
                    "recipe_id": row["recipe_id"],
                    "recipe_version": row["recipe_version"],
                    "recipe_allergen_tags": row["allergen_tags"],
                }
            )
        rows.append(catalog_row)

    projected = pd.DataFrame(rows)
    if projected.empty:
        metadata_columns = ["recipe_id", "recipe_version", "recipe_allergen_tags"] if include_metadata else []
        return pd.DataFrame(columns=[*CATALOG_COLUMNS, *metadata_columns])
    _validate_projected_catalog(projected)
    return projected if include_metadata else projected[CATALOG_COLUMNS]


def build_recipe_ingredient_grocery_list(
    tables: RecipeTables,
    recipe_servings: list[dict[str, object]],
) -> list[dict[str, Any]]:
    recipes = tables.recipes.set_index("recipe_id")
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for selection in recipe_servings:
        recipe_id = str(selection["recipe_id"])
        servings = _float_value(selection.get("servings"), 1.0)
        if recipe_id not in recipes.index:
            raise RecipeDataError(f"Unknown recipe_id in grocery selection: {recipe_id}")
        recipe = recipes.loc[recipe_id]
        factor = servings / float(recipe["servings_per_recipe"])
        ingredients = tables.ingredients.loc[
            (tables.ingredients["recipe_id"] == recipe_id) & (~tables.ingredients["is_optional"])
        ]
        for _, ingredient in ingredients.iterrows():
            allergen_tags = _join_tags(ingredient["contains_allergen_tags_list"])
            key = (str(ingredient["ingredient_role"]), str(ingredient["ingredient_name"]), allergen_tags)
            if key not in grouped:
                grouped[key] = {
                    "ingredient_role": key[0],
                    "ingredient_name": key[1],
                    "edible_grams": 0.0,
                    "recipe_count": 0,
                    "recipe_ids": set(),
                    "calories": 0.0,
                    "protein_g": 0.0,
                    "fiber_g": 0.0,
                    "sodium_mg": 0.0,
                    "allergen_tags": allergen_tags,
                }
            entry = grouped[key]
            grams = float(ingredient["edible_grams"]) * factor
            entry["edible_grams"] += grams
            entry["recipe_count"] += 1
            entry["recipe_ids"].add(recipe_id)
            entry["calories"] += float(ingredient["calories_per_100g"]) * grams / 100
            entry["protein_g"] += float(ingredient["protein_g_per_100g"]) * grams / 100
            entry["fiber_g"] += float(ingredient["fiber_g_per_100g"]) * grams / 100
            entry["sodium_mg"] += float(ingredient["sodium_mg_per_100g"]) * grams / 100

    rows = []
    for entry in grouped.values():
        rows.append(
            {
                "ingredient_role": entry["ingredient_role"],
                "ingredient_name": entry["ingredient_name"],
                "edible_grams": round(entry["edible_grams"], 1),
                "recipe_count": int(entry["recipe_count"]),
                "recipe_ids": ",".join(sorted(entry["recipe_ids"])),
                "calories": round(entry["calories"], 1),
                "protein_g": round(entry["protein_g"], 1),
                "fiber_g": round(entry["fiber_g"], 1),
                "sodium_mg": round(entry["sodium_mg"], 1),
                "allergen_tags": entry["allergen_tags"],
            }
        )
    return sorted(rows, key=lambda item: (item["ingredient_role"], item["ingredient_name"]))


def build_recipe_ingredient_grocery_list_from_items(
    tables: RecipeTables,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    projected = project_recipes_to_catalog(tables, include_metadata=True)
    if projected.empty:
        return []

    recipe_by_fdc_id = {
        int(row["fdc_id"]): {
            "recipe_id": str(row["recipe_id"]),
            "serving_grams": float(row["serving_grams"]),
        }
        for _, row in projected.iterrows()
    }

    selections: list[dict[str, object]] = []
    for item in items:
        try:
            fdc_id = int(float(item.get("fdc_id", 0) or 0))
        except (TypeError, ValueError):
            continue
        recipe = recipe_by_fdc_id.get(fdc_id)
        if recipe is None:
            continue
        base_serving_grams = _float_value(recipe["serving_grams"], 1.0)
        selected_grams = _float_value(item.get("serving_grams"), base_serving_grams)
        servings = selected_grams / base_serving_grams if base_serving_grams > 0 else 1.0
        selections.append({"recipe_id": recipe["recipe_id"], "servings": servings})

    if not selections:
        return []
    return build_recipe_ingredient_grocery_list(tables, selections)


def recipe_ingredient_grocery_csv(grocery_list: list[dict[str, Any]]) -> str:
    output = StringIO()
    fieldnames = [
        "ingredient_role",
        "ingredient_name",
        "edible_grams",
        "recipe_count",
        "recipe_ids",
        "calories",
        "protein_g",
        "fiber_g",
        "sodium_mg",
        "allergen_tags",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in grocery_list:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return output.getvalue()


def _read_contract_csv(path: Path, required_columns: tuple[str, ...]) -> pd.DataFrame:
    if not path.exists():
        raise RecipeDataError(f"Required recipe contract file not found: {path}")
    frame = pd.read_csv(path, keep_default_na=False)
    missing = set(required_columns) - set(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise RecipeDataError(f"{path.name} is missing required columns: {missing_text}")
    return frame.loc[:, list(required_columns)].copy()


def _normalize_recipes(recipes: pd.DataFrame) -> pd.DataFrame:
    result = recipes.copy()
    for column in [
        "servings_per_recipe",
        "serving_grams",
        "yield_grams",
        "default_portion_servings",
        "portion_min_servings",
        "portion_max_servings",
    ]:
        result[column] = _numeric_column(result, column)
    for column in ["prep_time_minutes", "cook_time_minutes"]:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0).astype(int)
    for column in ["meal_tags", "cuisine_tags", "dietary_pattern_tags", "allergen_tags"]:
        result[f"{column}_list"] = result[column].map(_split_tags)
    return result


def _normalize_ingredients(ingredients: pd.DataFrame) -> pd.DataFrame:
    result = ingredients.copy()
    for column in ["quantity", "edible_grams"]:
        result[column] = _numeric_column(result, column, allow_zero=True)
    for column in NUTRIENT_PER_100G_COLUMNS:
        result[column] = _numeric_column(result, column, allow_zero=True, allow_missing=True)
    for column in ["is_optional", "vegetarian", "vegan"]:
        result[column] = result[column].map(_to_bool)
    result["contains_allergen_tags_list"] = result["contains_allergen_tags"].map(_split_tags)
    return result


def _normalize_sources(sources: pd.DataFrame) -> pd.DataFrame:
    return sources.fillna("").copy()


def _validate_tables(tables: RecipeTables) -> None:
    if tables.recipes["recipe_id"].duplicated().any():
        raise RecipeDataError("recipes.csv contains duplicate recipe_id values")
    if tables.sources["source_id"].duplicated().any():
        raise RecipeDataError("recipe_sources.csv contains duplicate source_id values")
    if tables.ingredients[["recipe_id", "ingredient_id"]].duplicated().any():
        raise RecipeDataError("recipe_ingredients.csv contains duplicate ingredient_id values within a recipe")

    recipe_ids = set(tables.recipes["recipe_id"])
    source_ids = set(tables.sources["source_id"])
    missing_recipe_ids = sorted(set(tables.ingredients["recipe_id"]) - recipe_ids)
    if missing_recipe_ids:
        missing_text = ", ".join(missing_recipe_ids)
        raise RecipeDataError(f"recipe_ingredients.csv references unknown recipe_id values: {missing_text}")
    missing_sources = sorted(set(tables.recipes["source_id"]) - source_ids)
    if missing_sources:
        raise RecipeDataError(f"recipes.csv references unknown source_id values: {', '.join(missing_sources)}")
    if not set(tables.recipes["status"]).issubset(ALLOWED_STATUSES):
        raise RecipeDataError("recipes.csv contains unsupported status values")
    invalid_groups = sorted(set(tables.recipes["food_group_primary"]) - ALLOWED_FOOD_GROUPS)
    if invalid_groups:
        invalid_text = ", ".join(invalid_groups)
        raise RecipeDataError(f"recipes.csv contains unsupported food_group_primary values: {invalid_text}")
    invalid_roles = sorted(set(tables.ingredients["ingredient_role"]) - ALLOWED_INGREDIENT_ROLES)
    if invalid_roles:
        invalid_text = ", ".join(invalid_roles)
        raise RecipeDataError(f"recipe_ingredients.csv contains unsupported ingredient_role values: {invalid_text}")

    _require_positive(tables.recipes, "servings_per_recipe", "recipes.csv")
    _require_positive(tables.recipes, "serving_grams", "recipes.csv")
    _require_positive(tables.ingredients, "edible_grams", "recipe_ingredients.csv")
    _reject_missing_required_nutrients(tables.ingredients)
    _validate_dietary_tags(tables)


def _validate_dietary_tags(tables: RecipeTables) -> None:
    for _, recipe in tables.recipes.iterrows():
        recipe_id = str(recipe["recipe_id"])
        required = tables.ingredients.loc[
            (tables.ingredients["recipe_id"] == recipe_id) & (~tables.ingredients["is_optional"])
        ]
        tags = set(recipe["dietary_pattern_tags_list"])
        if "vegan" in tags and not bool(required["vegan"].all()):
            raise RecipeDataError(f"{recipe_id} is tagged vegan but has non-vegan required ingredients")
        if "vegetarian" in tags and not bool(required["vegetarian"].all()):
            raise RecipeDataError(f"{recipe_id} is tagged vegetarian but has non-vegetarian required ingredients")


def _reject_missing_required_nutrients(ingredients: pd.DataFrame) -> None:
    required = ingredients.loc[~ingredients["is_optional"]]
    for column in NUTRIENT_PER_100G_COLUMNS:
        missing = required[column].isna()
        if missing.any():
            bad = required.loc[missing, ["recipe_id", "ingredient_id"]].head(3)
            examples = "; ".join(f"{row.recipe_id}/{row.ingredient_id}" for row in bad.itertuples())
            message = f"recipe_ingredients.csv has missing required nutrient values in {column}: {examples}"
            raise RecipeDataError(message)


def _validate_projected_catalog(projected: pd.DataFrame) -> None:
    missing = set(CATALOG_COLUMNS) - set(projected.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise RecipeDataError(f"Projected recipe catalog is missing required columns: {missing_text}")
    if projected["fdc_id"].duplicated().any():
        raise RecipeDataError("Projected recipe catalog contains duplicate fdc_id values")
    if not (projected["serving_grams"] > 0).all():
        raise RecipeDataError("Projected recipe catalog serving_grams must be positive")


def _numeric_column(
    frame: pd.DataFrame,
    column: str,
    *,
    allow_zero: bool = False,
    allow_missing: bool = False,
) -> pd.Series:
    raw = frame[column].astype(str).str.strip()
    missing = raw.eq("")
    converted = pd.to_numeric(raw.mask(missing), errors="coerce")
    if converted.isna().any() and not allow_missing:
        raise RecipeDataError(f"{column} contains missing required nutrient or numeric values")
    if allow_zero:
        if (converted.dropna() < 0).any():
            raise RecipeDataError(f"{column} must be non-negative")
    elif (converted.dropna() <= 0).any():
        raise RecipeDataError(f"{column} must be positive")
    return converted


def _require_positive(frame: pd.DataFrame, column: str, filename: str) -> None:
    if (frame[column] <= 0).any():
        raise RecipeDataError(f"{filename} column {column} must be positive")


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float_value(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(str(value))
    except ValueError:
        return default


def _split_tags(value: object) -> tuple[str, ...]:
    text = str(value or "").strip()
    if not text:
        return ()
    return tuple(tag.strip().lower() for tag in text.split(",") if tag.strip())


def _join_tags(tags: list[str] | tuple[str, ...]) -> str:
    return ",".join(sorted(set(tag for tag in tags if tag)))


def _stable_recipe_fdc_id(recipe_id: str) -> int:
    digest = sha1(recipe_id.encode("utf-8")).hexdigest()
    return 980_000_000 + (int(digest[:8], 16) % 10_000_000)
