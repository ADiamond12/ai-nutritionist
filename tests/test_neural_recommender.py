from ai_nutritionist.data import load_food_catalog
from ai_nutritionist.profile import build_profile
from ai_nutritionist.recommender import recommend


def test_catalog_is_expanded_and_has_conservative_vegan_flags():
    catalog = load_food_catalog()

    assert len(catalog) >= 700
    assert "vegan" in catalog.columns
    assert catalog["vegan"].sum() >= 100
    assert catalog.loc[catalog["vegan"], "vegetarian"].all()
    assert {"protein", "vegetable", "fruit", "whole_grain", "healthy_fat"}.issubset(set(catalog["food_group"]))


def test_catalog_includes_curated_mediterranean_greek_foods():
    catalog = load_food_catalog()
    names = set(catalog["food_name"])

    assert "Greek yogurt bowl with berries and walnuts" in names
    assert "Greek salad with chicken souvlaki and whole wheat pita" in names
    assert "Fasolada bean soup with carrots celery and olive oil" in names
    assert "Grilled salmon with horta and lemon potatoes" in names
    curated_rows = catalog.loc[
        catalog["food_name"].isin(
            [
                "Greek yogurt bowl with berries and walnuts",
                "Greek salad with chicken souvlaki and whole wheat pita",
                "Fasolada bean soup with carrots celery and olive oil",
                "Grilled salmon with horta and lemon potatoes",
            ]
        )
    ]
    assert curated_rows["source"].str.contains("Curated Mediterranean").all()


def test_vegan_recommendations_are_vegan_and_not_repeated_across_the_day():
    result = recommend(
        weight_kg=72,
        height_cm=178,
        age=34,
        sex="male",
        activity="moderate",
        dietary_pattern="vegan",
        top_k=4,
    )

    all_items = [item for meal in result.meals for item in meal.items]
    assert all_items
    assert all(item["vegan"] for item in all_items)
    assert len({item["fdc_id"] for item in all_items}) == len(all_items)


def test_neural_ranker_returns_reproducible_ranked_scores():
    from ai_nutritionist.ranker import rank_foods_with_neural_model

    catalog = load_food_catalog().head(200)
    profile = build_profile(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate")

    first = rank_foods_with_neural_model(catalog, profile, "Lunch")
    second = rank_foods_with_neural_model(catalog, profile, "Lunch")

    assert "neural_score" in first.columns
    assert first.attrs["ranker_algorithm"].startswith("MLP")
    assert first["neural_score"].tolist() == second["neural_score"].tolist()
    assert first.iloc[0]["neural_score"] >= first.iloc[-1]["neural_score"]


def test_meal_recommendations_include_practical_titles():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate", top_k=4)

    for meal in result.meals:
        assert meal.title
        assert " with " in meal.title.lower() or "mediterranean plate:" in meal.title.lower()
        assert meal.model_name.startswith("Neural")


def test_common_vegan_plan_avoids_impractical_or_high_sugar_standalone_items():
    profiles = [
        {"weight_kg": 68, "height_cm": 172, "age": 32, "sex": "female"},
        {"weight_kg": 75, "height_cm": 180, "age": 30, "sex": "male"},
    ]
    for profile in profiles:
        result = recommend(
            **profile,
            activity="moderate",
            dietary_pattern="vegan",
            top_k=4,
        )

        names = " ".join(item["food_name"].lower() for meal in result.meals for item in meal.items)
        assert "papad" not in names
        assert "puri" not in names
        assert "candied" not in names
        assert "corn beverage" not in names
        assert "lime, raw" not in names
        assert "lemon, raw" not in names
        assert "textured vegetable protein, dry" not in names
        assert "tortellini" not in names
        assert "ravioli" not in names

        breakfast = next(meal for meal in result.meals if meal.name == "Breakfast")
        breakfast_names = " ".join(item["food_name"].lower() for item in breakfast.items)
        assert "beans" not in breakfast_names

        for meal in result.meals:
            assert meal.guidance_checks["sugars_within_meal_limit"]
            assert meal.totals["calories"] <= result.daily_targets.calories * 0.45


def test_lunch_and_dinner_do_not_use_breakfast_cereal_or_repeat_food_families():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate", top_k=4)

    family_names = []
    for meal in result.meals:
        for item in meal.items:
            family_names.append(item["food_name"].split(",")[0].strip().lower())
            if meal.name in {"Lunch", "Dinner"}:
                assert "cereal" not in item["food_name"].lower()

    assert len(family_names) == len(set(family_names))


def test_omnivore_lunch_or_dinner_uses_animal_protein_when_allowed():
    result = recommend(weight_kg=75, height_cm=180, age=30, sex="male", activity="moderate", top_k=4)

    lunch_dinner_proteins = [
        item
        for meal in result.meals
        if meal.name in {"Lunch", "Dinner"}
        for item in meal.items
        if item["food_group"] == "protein"
    ]

    assert any(not item["vegetarian"] for item in lunch_dinner_proteins)

    names = " ".join(item["food_name"].lower() for meal in result.meals for item in meal.items)
    assert "eel" not in names
    assert "mock chicken" not in names
    assert "with dressing" not in names


def test_default_plan_uses_practical_mediterranean_foods_for_large_profile():
    result = recommend(
        weight_kg=125,
        height_cm=200,
        age=30,
        sex="male",
        activity="moderate",
        top_k=4,
    )

    names = [item["food_name"].lower() for meal in result.meals for item in meal.items]
    joined_names = " ".join(names)
    curated_count = sum(
        "Curated Mediterranean" in item["source"] for meal in result.meals for item in meal.items
    )

    assert curated_count >= 7
    assert "pumpkin seeds" not in joined_names
    assert "flax seeds" not in joined_names
    assert "chia seeds" not in joined_names
    assert "sprouts" not in joined_names
    assert result.daily_totals["calories"] >= result.daily_targets.calories * 0.70
    assert result.daily_totals["protein_g"] >= result.daily_targets.protein_g * 0.75


def test_mediterranean_pattern_is_explicitly_supported():
    result = recommend(
        weight_kg=88,
        height_cm=180,
        age=45,
        sex="male",
        activity="moderate",
        dietary_pattern="mediterranean",
        top_k=4,
    )

    curated_count = sum(
        "Curated Mediterranean" in item["source"] for meal in result.meals for item in meal.items
    )

    assert result.preferences["dietary_pattern"] == "mediterranean"
    assert curated_count >= 6
