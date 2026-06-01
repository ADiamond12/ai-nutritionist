# Data Card

## Dataset Inventory

- `data/foods_catalog.csv`: 2,014 processed project rows derived from USDA/FNDDS data
- `data/mediterranean_foods.csv`: 35 curated Mediterranean/Greek extension rows
- `data/huggingface/food_ranker_items.csv`: 2,049 combined rows for optional hosted dataset browsing

The combined export contains 754 protein rows, 622 whole-grain/starch rows, 449 vegetable rows, 122 healthy-fat rows, and 102 fruit rows. It includes 1,554 rows marked vegetarian and 1,132 rows marked vegan by conservative project heuristics.

## Provenance

The runtime catalog is derived from USDA FoodData Central FNDDS 2021-2023 CSV data, release date October 2024. The public repository includes the processed catalog and not the full USDA archive.

The project also includes a curated Mediterranean/Greek extension with USDA-style nutrient estimates for practical foods such as Greek yogurt bowls, dakos-style toast, lentil soup, fasolada, chickpea salad, grilled fish, horta, Greek salads, and olive-oil vegetable sides.

Source reference: https://fdc.nal.usda.gov/download-datasets/

## Schema

Runtime rows use a shared schema: `fdc_id`, `food_name`, WWEIA category fields, `food_group`, `meal_tags`, `serving_grams`, calories, protein, carbohydrate, fat, fiber, sugars, sodium, saturated fat, vegetarian flag, vegan flag, minimally processed flag, and source.

## Processing Pipeline

`scripts/build_food_catalog.py` downloads or reads the USDA FNDDS ZIP archive, joins food descriptions, survey foods, WWEIA category data, and nutrient tables, filters rows for public recommendation use, derives serving sizes and flags, then writes the processed catalog and Hugging Face-compatible export.

Rebuild command:

```bash
python scripts/build_food_catalog.py
```

## Intended Use

The data is intended for local recommender training/ranking, catalog browsing, tests, and public portfolio review of a general wellness planning system.

## Not Suitable For

The data is not suitable for clinical dietetics, allergy safety, micronutrient sufficiency, medication interactions, disease-specific meal planning, therapeutic ketogenic diets, or added-sugar analysis.

## Quality Controls

The runtime loader validates required columns, converts numeric and boolean fields, and merges the Mediterranean extension when present. Tests cover schema shape, catalog variety, dietary filters, meal tags, source distribution, recommendation output shape, and evaluation behavior.

## Known Limitations

- Some USDA nutrient values come from broad food descriptions rather than exact recipes.
- The curated Mediterranean extension uses estimated USDA-style components.
- Total sugars are not added sugars.
- Vegetarian, vegan, and minimally processed flags are project heuristics.
- The catalog does not encode allergies, medications, budget, availability, cooking method, appetite, disease state, medical history, or clinician guidance.

## Privacy And Licensing Posture

No personally identifiable information is included in the committed datasets. The full USDA archive is intentionally omitted. User feedback CSV exports are separate local user data and should not be committed.
