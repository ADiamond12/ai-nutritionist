import pandas as pd

from ai_nutritionist.metrics import calculate_bmi, filter_foods_by_veg, macro_totals


def test_bmi_category_logic_uses_expected_thresholds():
    assert calculate_bmi(weight_kg=45, height_cm=170).category_id == 0
    assert calculate_bmi(weight_kg=52, height_cm=170).category_id == 1
    assert calculate_bmi(weight_kg=70, height_cm=170).category_id == 2
    assert calculate_bmi(weight_kg=83, height_cm=170).category_id == 3
    assert calculate_bmi(weight_kg=95, height_cm=170).category_id == 4


def test_macro_totals_use_named_carbohydrate_fibre_and_sugar_columns():
    items = [
        {
            "Food_items": "Sample oats",
            "Calories": 120,
            "Fats": 2.5,
            "Proteins": 6,
            "Carbohydrates": 21,
            "Fibre": 4,
            "Sugars": 1.5,
        },
        {
            "Food_items": "Sample berries",
            "Calories": 80,
            "Fats": 0.5,
            "Proteins": 1,
            "Carbohydrates": 19,
            "Fibre": 5,
            "Sugars": 11,
        },
    ]

    totals = macro_totals(items)

    assert totals == {
        "Calories": 200.0,
        "Fats": 3.0,
        "Proteins": 7.0,
        "Carbohydrates": 40.0,
        "Fibre": 9.0,
        "Sugars": 12.5,
    }


def test_veg_filter_keeps_legacy_vegetarian_flags():
    foods = pd.DataFrame(
        [
            {"Food_items": "Veg item", "VegNovVeg": "0"},
            {"Food_items": "Non veg item", "VegNovVeg": "1"},
            {"Food_items": "Unknown item", "VegNovVeg": " "},
        ]
    )

    assert filter_foods_by_veg(foods, -1)["Food_items"].tolist() == [
        "Veg item",
        "Non veg item",
        "Unknown item",
    ]
    assert filter_foods_by_veg(foods, 0)["Food_items"].tolist() == ["Veg item"]
    assert filter_foods_by_veg(foods, 1)["Food_items"].tolist() == ["Non veg item"]
