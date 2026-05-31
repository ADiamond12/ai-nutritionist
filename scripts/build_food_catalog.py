import argparse
import csv
import tempfile
import urllib.request
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


SOURCE_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_csv_2024-10-31.zip"
ZIP_ROOT = "FoodData_Central_survey_food_csv_2024-10-31"
SOURCE_LABEL = "USDA FoodData Central FNDDS 2021-2023, October 2024 release"

NUTRIENT_IDS = {
    "calories": 208,
    "protein_g": 203,
    "fat_g": 204,
    "carbohydrate_g": 205,
    "fiber_g": 291,
    "sugars_g": 269,
    "sodium_mg": 307,
    "saturated_fat_g": 606,
}

FRUIT_CODES = {6002, 6004, 6006, 6008, 6009, 6011, 6012, 6014, 6016, 6018, 6020, 6022, 6024}
VEGETABLE_CODES = {6402, 6404, 6406, 6407, 6409, 6410, 6411, 6412, 6413, 6414, 6416, 6418, 6420, 6432, 6802}
GRAIN_CODES = {4002, 4004, 4202, 4204, 4206, 4208, 4404, 4604, 4802, 4804}
PROTEIN_CODES = {
    1006,
    1008,
    1604,
    1820,
    1822,
    1902,
    1904,
    2002,
    2004,
    2006,
    2008,
    2202,
    2206,
    2402,
    2404,
    2502,
    2802,
    2806,
    3102,
}
HEALTHY_FAT_CODES = {2804, 8004, 8012, 8408}
MIXED_OPTION_CODES = {3104, 3202, 3204, 3404, 3744}

INCLUDED_CODES = FRUIT_CODES | VEGETABLE_CODES | GRAIN_CODES | PROTEIN_CODES | HEALTHY_FAT_CODES | MIXED_OPTION_CODES

EXCLUDED_DESCRIPTION_TERMS = {
    "baby food",
    "infant formula",
    "human milk",
    "not specified",
    "nfs",
    "quantity not specified",
    "candy",
    "soft drink",
    "sport drink",
    "energy drink",
    "liquor",
    "cocktail",
    "beer",
    "wine",
    "doughnut",
    "pastry",
    "cookie",
    "brownie",
    "cake",
    "pie",
    "ice cream",
    "sorbet",
    "pudding",
    "candied",
    "papad",
    "puri",
    "textured vegetable protein, dry",
    "protein powder",
    "corn beverage",
    "lemon, raw",
    "lime, raw",
    "with dressing",
    "mock",
    "eel",
    "fried, coated",
    "from fast food",
}

ANIMAL_TERMS = {
    "beef",
    "pork",
    "lamb",
    "goat",
    "game",
    "chicken",
    "turkey",
    "duck",
    "fish",
    "salmon",
    "tuna",
    "cod",
    "tilapia",
    "shrimp",
    "crab",
    "lobster",
    "oyster",
    "clam",
    "shellfish",
    "seafood",
    "ham",
    "bacon",
    "sausage",
    "frankfurter",
    "pepperoni",
    "egg",
    "omelet",
    "cheese",
    "milk",
    "yogurt",
    "cream",
    "butter",
    "mayonnaise",
    "honey",
}

VEGETARIAN_ANIMAL_TERMS = {
    "beef",
    "pork",
    "lamb",
    "goat",
    "game",
    "chicken",
    "turkey",
    "duck",
    "fish",
    "salmon",
    "tuna",
    "cod",
    "tilapia",
    "shrimp",
    "crab",
    "lobster",
    "oyster",
    "clam",
    "shellfish",
    "seafood",
    "ham",
    "bacon",
    "sausage",
    "frankfurter",
    "pepperoni",
}

NON_VEGAN_CATEGORY_CODES = {
    1002,
    1004,
    1006,
    1008,
    1202,
    1204,
    1206,
    1208,
    1402,
    1602,
    1604,
    1820,
    1822,
    2002,
    2004,
    2006,
    2008,
    2010,
    2202,
    2204,
    2206,
    2402,
    2404,
    2502,
    2602,
    2604,
    2606,
    2608,
    8002,
    8006,
    8008,
    8010,
}

NON_VEGETARIAN_CATEGORY_CODES = {
    2002,
    2004,
    2006,
    2008,
    2010,
    2202,
    2204,
    2206,
    2402,
    2404,
    2602,
    2604,
    2606,
    2608,
}

HIGHLY_PROCESSED_CODES = {
    2204,
    2602,
    2604,
    2606,
    2608,
    5002,
    5004,
    5008,
    5402,
    5404,
    5502,
    5504,
    5506,
    5702,
    5704,
    5802,
    5804,
    6804,
    7202,
    7204,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the USDA-backed processed food catalog.")
    parser.add_argument("--zip-path", type=Path, default=Path(tempfile.gettempdir()) / "fdc-fndds-2024.zip")
    parser.add_argument("--output", type=Path, default=Path("data/foods_catalog.csv"))
    parser.add_argument(
        "--hf-output",
        type=Path,
        default=Path("data/huggingface/food_ranker_items.csv"),
        help="Optional Hugging Face compatible CSV export for read-only dataset use.",
    )
    parser.add_argument(
        "--mediterranean-extension",
        type=Path,
        default=Path("data/mediterranean_foods.csv"),
        help="Optional curated Mediterranean/Greek extension merged into the Hugging Face export.",
    )
    args = parser.parse_args()

    if not args.zip_path.exists():
        args.zip_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SOURCE_URL, args.zip_path)

    catalog = build_catalog(args.zip_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(args.output, index=False, quoting=csv.QUOTE_MINIMAL)

    hf_catalog = _merge_optional_extension(catalog, args.mediterranean_extension)
    args.hf_output.parent.mkdir(parents=True, exist_ok=True)
    hf_catalog.to_csv(args.hf_output, index=False, quoting=csv.QUOTE_MINIMAL)
    return 0


def _merge_optional_extension(catalog: pd.DataFrame, extension_path: Path) -> pd.DataFrame:
    if not extension_path.exists():
        return catalog
    extension = pd.read_csv(extension_path)
    missing = set(catalog.columns) - set(extension.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Mediterranean extension is missing required columns: {missing_text}")
    return pd.concat([catalog, extension[catalog.columns]], ignore_index=True).drop_duplicates("fdc_id")


def build_catalog(zip_path: Path) -> pd.DataFrame:
    with ZipFile(zip_path) as archive:
        food = pd.read_csv(archive.open(f"{ZIP_ROOT}/food.csv"))
        survey = pd.read_csv(archive.open(f"{ZIP_ROOT}/survey_fndds_food.csv"))
        categories = pd.read_csv(archive.open(f"{ZIP_ROOT}/wweia_food_category.csv"))
        nutrient = pd.read_csv(archive.open(f"{ZIP_ROOT}/food_nutrient.csv"))

    food = (
        food.merge(survey[["fdc_id", "wweia_category_number"]], on="fdc_id", how="left")
        .merge(
            categories,
            left_on="wweia_category_number",
            right_on="wweia_food_category",
            how="left",
        )
        .rename(
            columns={
                "description": "food_name",
                "wweia_category_number": "wweia_category",
                "wweia_food_category_description": "wweia_category_description",
            }
        )
    )

    nutrient_pivot = (
        nutrient[nutrient["nutrient_id"].isin(NUTRIENT_IDS.values())]
        .pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first")
        .rename(columns={value: key for key, value in NUTRIENT_IDS.items()})
        .reset_index()
    )
    catalog = food.merge(nutrient_pivot, on="fdc_id", how="left")
    catalog = catalog.loc[catalog["wweia_category"].isin(INCLUDED_CODES)].copy()
    catalog = catalog.loc[catalog["food_name"].map(_is_public_recommendation_food)].copy()

    catalog["food_group"] = catalog.apply(_food_group, axis=1)
    catalog = catalog.loc[catalog["food_group"].ne("exclude")].copy()
    catalog["serving_grams"] = catalog.apply(_serving_grams, axis=1)

    for column in NUTRIENT_IDS:
        catalog[column] = pd.to_numeric(catalog[column], errors="coerce").fillna(0)
        catalog[column] = (catalog[column] * catalog["serving_grams"] / 100).round(1)

    catalog["meal_tags"] = catalog.apply(_meal_tags, axis=1)
    catalog["vegetarian"] = catalog.apply(_is_vegetarian, axis=1)
    catalog["vegan"] = catalog.apply(_is_vegan, axis=1)
    catalog["minimally_processed"] = catalog.apply(_is_minimally_processed, axis=1)
    catalog["source"] = SOURCE_LABEL

    catalog = catalog.loc[catalog["calories"].between(15, 700)].copy()
    catalog = catalog.loc[catalog["meal_tags"].ne("")].copy()
    catalog = catalog.drop_duplicates(subset=["fdc_id"]).sort_values(["food_group", "food_name"]).reset_index(drop=True)

    return catalog[
        [
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
    ]


def _is_public_recommendation_food(food_name: object) -> bool:
    text = str(food_name).lower()
    return not any(term in text for term in EXCLUDED_DESCRIPTION_TERMS)


def _food_group(row: pd.Series) -> str:
    code = int(row["wweia_category"])
    description = str(row["food_name"]).lower()
    category = str(row["wweia_category_description"]).lower()

    if code in FRUIT_CODES:
        if "avocado" in description:
            return "healthy_fat"
        return "fruit"
    if code in VEGETABLE_CODES:
        return "vegetable"
    if code in HEALTHY_FAT_CODES:
        return "healthy_fat"
    if code in GRAIN_CODES:
        return "whole_grain"
    if code in PROTEIN_CODES:
        return "protein"
    if code in MIXED_OPTION_CODES:
        if any(term in category for term in ["vegetable", "bean", "soy"]):
            return "protein" if "bean" in category or "soy" in category else "vegetable"
        if any(term in category for term in ["rice", "pasta"]):
            return "whole_grain"
        if "smoothies" in category:
            return "fruit"
        if "vegetable sandwiches" in category:
            return "protein"
    return "exclude"


def _serving_grams(row: pd.Series) -> float:
    code = int(row["wweia_category"])
    group = row["food_group"]
    description = str(row["food_name"]).lower()

    if group == "healthy_fat":
        if "oil" in description or "dressing" in description:
            return 10.0
        if "avocado" in description or "olives" in description:
            return 65.0
        return 18.0
    if group == "fruit":
        if "dried" in description:
            return 40.0
        if "juice" in description or "smoothie" in description:
            return 240.0
        return 140.0
    if group == "vegetable":
        if "potato" in description:
            return 160.0
        return 110.0
    if group == "whole_grain":
        if code in {4202, 4204, 4206, 4208}:
            return 55.0
        if code in {4604, 4802, 4804}:
            return 45.0
        return 150.0
    if group == "protein":
        if code in {1006, 1008, 1902}:
            return 240.0
        if code in {1820, 1822, 1904}:
            return 170.0
        if code in {2802, 2806, 3102}:
            return 150.0
        if code == 2502:
            return 100.0
        return 120.0
    return 100.0


def _meal_tags(row: pd.Series) -> str:
    code = int(row["wweia_category"])
    group = row["food_group"]
    description = str(row["food_name"]).lower()
    tags = set()

    if group in {"fruit", "healthy_fat"}:
        tags.update({"breakfast", "lunch", "dinner"})
    if group == "vegetable":
        tags.update({"lunch", "dinner"})
        if any(term in description for term in ["tomato", "spinach", "avocado"]):
            tags.add("breakfast")
    if group == "whole_grain":
        if code in {4404, 4604, 4802, 4804}:
            tags.add("breakfast")
        elif code in {4202, 4204, 4206, 4208}:
            tags.update({"breakfast", "lunch", "dinner"})
        else:
            tags.update({"lunch", "dinner"})
    if group == "protein":
        tags.update({"lunch", "dinner"})
        if code in {1006, 1008, 1604, 1820, 1822, 1902, 1904, 2502}:
            tags.add("breakfast")
    return ",".join(sorted(tags))


def _is_vegetarian(row: pd.Series) -> bool:
    code = int(row["wweia_category"])
    if code in NON_VEGETARIAN_CATEGORY_CODES:
        return False
    return not _contains_any(row["food_name"], VEGETARIAN_ANIMAL_TERMS)


def _is_vegan(row: pd.Series) -> bool:
    code = int(row["wweia_category"])
    if code in NON_VEGAN_CATEGORY_CODES:
        return False
    if not _is_vegetarian(row):
        return False
    text = str(row["food_name"]).lower()
    if any(term in text for term in ["tortellini", "ravioli"]):
        return False
    if "plant-based milk" in str(row["wweia_category_description"]).lower():
        return True
    if "plant-based yogurt" in str(row["wweia_category_description"]).lower():
        return True
    return not any(term in text for term in ANIMAL_TERMS)


def _is_minimally_processed(row: pd.Series) -> bool:
    code = int(row["wweia_category"])
    description = str(row["food_name"]).lower()
    if code in HIGHLY_PROCESSED_CODES:
        return False
    if any(
        term in description
        for term in ["fried", "breaded", "coated", "sweetened", "flavored", "fillet", "nugget", "patty"]
    ):
        return False
    if code in {1602, 8004, 8012, 8408}:
        return False
    return True


def _contains_any(value: object, terms: set[str]) -> bool:
    text = str(value).lower()
    return any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
