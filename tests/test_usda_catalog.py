from ai_nutritionist.data import load_food_catalog


def test_usda_catalog_has_system_schema_and_enough_variety():
    catalog = load_food_catalog()

    required = {
        "fdc_id",
        "food_name",
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
        "minimally_processed",
    }

    assert required.issubset(catalog.columns)
    assert len(catalog) >= 35
    assert {"protein", "vegetable", "fruit", "whole_grain"}.issubset(set(catalog["food_group"]))
    assert catalog["fdc_id"].notna().all()
    assert (catalog["serving_grams"] > 0).all()


def test_usda_catalog_meal_tags_cover_all_meals():
    catalog = load_food_catalog()
    tags = set(",".join(catalog["meal_tags"]).split(","))

    assert {"breakfast", "lunch", "dinner"}.issubset(tags)
