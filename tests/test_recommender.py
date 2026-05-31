from ai_nutritionist.recommender import recommend


def test_recommendation_output_shape_is_portfolio_safe():
    result = recommend(weight_kg=75, height_cm=180, age=24, top_k=3)

    assert result.bmi.value == 23.1
    assert result.bmi.category_label == "Normal"
    assert "not medical advice" in result.disclaimer.lower()
    assert [meal.name for meal in result.meals] == ["Breakfast", "Lunch", "Dinner"]
    assert all(0 < len(meal.items) <= 3 for meal in result.meals)

    first_item = result.meals[0].items[0]
    assert {
        "Food_items",
        "Calories",
        "Fats",
        "Proteins",
        "Carbohydrates",
        "Fibre",
        "Sugars",
        "VegNovVeg",
    }.issubset(first_item)


def test_recommendation_output_is_reproducible_for_same_input():
    first = recommend(weight_kg=75, height_cm=180, age=24, top_k=5).to_dict()
    second = recommend(weight_kg=75, height_cm=180, age=24, top_k=5).to_dict()

    assert first == second


def test_veg_filter_applies_to_recommendation_items():
    result = recommend(weight_kg=75, height_cm=180, age=24, top_k=5, veg_filter=0)

    for meal in result.meals:
        assert meal.items
        assert {item["VegNovVeg"] for item in meal.items} == {"0"}
