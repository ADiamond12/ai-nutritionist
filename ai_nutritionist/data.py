from pathlib import Path

import pandas as pd

from ai_nutritionist.constants import (
    CATALOG_COLUMNS,
    DEFAULT_DATA_DIR,
    FOOD_CATALOG_FILENAME,
    MEDITERRANEAN_CATALOG_FILENAME,
)


def resolve_data_path(filename: str, data_dir: Path | str | None = None) -> Path:
    base_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    path = (base_dir / filename).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Required nutrition data file not found: {path}")
    return path


def load_food_catalog(data_dir: Path | str | None = None) -> pd.DataFrame:
    base_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    df = pd.read_csv(resolve_data_path(FOOD_CATALOG_FILENAME, data_dir))
    mediterranean_path = (base_dir / MEDITERRANEAN_CATALOG_FILENAME).resolve()
    if mediterranean_path.exists():
        mediterranean_df = pd.read_csv(mediterranean_path)
        df = pd.concat([df, mediterranean_df], ignore_index=True)

    missing = set(CATALOG_COLUMNS) - set(df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Food catalog is missing required columns: {missing_text}")

    df = df.copy()
    text_columns = ["food_name", "wweia_category_description", "food_group", "meal_tags", "source"]
    for column in text_columns:
        df[column] = df[column].fillna("").astype(str)

    numeric_columns = [
        "fdc_id",
        "wweia_category",
        "serving_grams",
        "calories",
        "protein_g",
        "carbohydrate_g",
        "fat_g",
        "fiber_g",
        "sugars_g",
        "sodium_mg",
        "saturated_fat_g",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    for column in ["vegetarian", "vegan", "minimally_processed"]:
        df[column] = df[column].map(_to_bool)
    return df[CATALOG_COLUMNS].reset_index(drop=True)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_food_data(data_dir: Path | str | None = None) -> pd.DataFrame:
    """Backward-compatible alias for older callers."""
    return load_food_catalog(data_dir)


def split_foods_by_meal(food_data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    meals = {}
    for meal_name in ["Breakfast", "Lunch", "Dinner"]:
        tag = meal_name.lower()
        mask = food_data["meal_tags"].str.lower().str.split(",").apply(lambda tags: tag in {t.strip() for t in tags})
        meals[meal_name] = food_data.loc[mask].reset_index(drop=True)
    return meals
