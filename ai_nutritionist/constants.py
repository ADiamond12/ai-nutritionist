from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

FOOD_CATALOG_FILENAME = "foods_catalog.csv"
MEDITERRANEAN_CATALOG_FILENAME = "mediterranean_foods.csv"

SYSTEM_NAME = "AI Nutritionist"

MEAL_NAMES = ["Breakfast", "Lunch", "Dinner"]

CATALOG_COLUMNS = [
    "fdc_id",
    "food_name",
    "wweia_category",
    "wweia_category_description",
    "food_group",
    "meal_tags",
    "serving_grams",
    "calories",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sugars_g",
    "sodium_mg",
    "saturated_fat_g",
    "vegetarian",
    "vegan",
    "minimally_processed",
    "source",
]

SAFETY_DISCLAIMER = (
    "AI Nutritionist provides general wellness nutrition suggestions only; "
    "it is not medical advice and does not diagnose, treat, or manage health conditions. "
    "Consult a qualified professional for personal dietary or medical decisions."
)
