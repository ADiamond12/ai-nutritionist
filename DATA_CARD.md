# Data Card

## Dataset Inventory

- `data/foods_catalog.csv`: 2,014 processed project rows derived from USDA/FNDDS data
- `data/mediterranean_foods.csv`: 35 curated Mediterranean/Greek extension rows
- `data/recipes/`: 9 reviewed recipe-backed Mediterranean/Greek pilot rows with ingredient-level curated estimates
- `data/huggingface/food_ranker_items.csv`: 2,049 combined rows for optional hosted dataset browsing

The runtime catalog contains 2,058 rows after optional recipe projection: 763 protein rows, 622 whole-grain/starch rows, 449 vegetable rows, 122 healthy-fat rows, and 102 fruit rows. It includes 1,559 rows marked vegetarian and 1,135 rows marked vegan by conservative project heuristics. The Hugging Face-compatible flat browsing export remains 2,049 rows.

## Provenance

The runtime catalog is derived from USDA FoodData Central FNDDS 2021-2023 CSV data, release date October 2024. The public repository includes the processed catalog and not the full USDA archive.

The project also includes a curated Mediterranean/Greek extension with USDA-style nutrient estimates for practical foods such as Greek yogurt bowls, dakos-style toast, lentil soup, fasolada, chickpea salad, grilled fish, horta, Greek salads, and olive-oil vegetable sides.

The `data/recipes/` pilot adds nine ingredient-level Mediterranean/Greek recipes. Each recipe has source metadata, review status fields, ingredient rows, dietary flags, allergen tags, and per-100g nutrient estimates that are aggregated deterministically before projection into the runtime catalog.

Source reference: https://fdc.nal.usda.gov/download-datasets/

## Schema

Runtime rows use a shared schema: `fdc_id`, `food_name`, WWEIA category fields, `food_group`, `meal_tags`, `serving_grams`, calories, protein, carbohydrate, fat, fiber, sugars, sodium, saturated fat, vegetarian flag, vegan flag, minimally processed flag, and source.

Recipe-backed rows are projected into the same public schema. Internal recipe IDs, review notes, and source-table metadata are not part of the default public recommendation payload. Ingredient-level grocery exports are generated only when selected foods can be matched back to reviewed recipe-backed rows.

## Processing Pipeline

`scripts/build_food_catalog.py` downloads or reads the USDA FNDDS ZIP archive, joins food descriptions, survey foods, WWEIA category data, and nutrient tables, filters rows for public recommendation use, derives serving sizes and flags, then writes the processed catalog and Hugging Face-compatible export. Runtime loading also validates `data/recipes/` when present and appends reviewed recipe projections to the in-app catalog.

Rebuild command:

```bash
python scripts/build_food_catalog.py
```

## Intended Use

The data is intended for local recommender training/ranking, catalog browsing, tests, and public portfolio review of a general wellness planning system.

## Not Suitable For

The data is not suitable for clinical dietetics, allergy safety, micronutrient sufficiency, medication interactions, disease-specific meal planning, therapeutic ketogenic diets, or added-sugar analysis.

## Quality Controls

The runtime loader validates required columns, converts numeric and boolean fields, merges the Mediterranean extension when present, and validates/projects reviewed recipe rows when `data/recipes/` exists. Tests cover schema shape, catalog variety, recipe fixture math, missing-nutrient rejection, dietary/allergen derivation, dietary filters, meal tags, source distribution, recommendation output shape, public payload boundaries, and evaluation behavior.

Generated grocery lists are derived from recommendation outputs at runtime. Flat grocery lists group selected catalog rows. Ingredient grocery lists are available for recipe-backed pilot rows only. Generated outputs are not a separate dataset and are not committed unless a reviewer intentionally creates sample artifacts.

## Known Limitations

- Some USDA nutrient values come from broad food descriptions rather than exact recipes.
- The curated Mediterranean extension and recipe pilot use estimated USDA-style components.
- Atomic foods, mixed dishes, curated complete dishes, and recipe-backed pilot rows share one flat runtime catalog schema.
- Only the nine reviewed recipe-backed pilot rows can be expanded into ingredient-level grocery rows. Other grocery-list rows remain grouped catalog items.
- `docs/RECIPE_DATA_CONTRACT.md` defines the recipe data contract and migration path; it is a data-engineering boundary, not clinical validation.
- Total sugars are not added sugars.
- Vegetarian, vegan, and minimally processed flags are project heuristics.
- The catalog does not encode allergies, medications, budget, availability, cooking method, appetite, disease state, medical history, or clinician guidance.

## Privacy And Licensing Posture

No personally identifiable information is included in the committed datasets. The full USDA archive is intentionally omitted. User feedback CSV exports and optional local SQLite feedback databases are separate local user data and should not be committed.
