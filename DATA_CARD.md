# Data Card

## Data Sources

The runtime catalog is derived from USDA FoodData Central FNDDS 2021-2023 CSV data, release date October 2024. The public repo includes a processed catalog for local demonstration and tests.

The project also includes a curated Mediterranean/Greek extension with USDA-style nutrient estimates for practical foods such as Greek yogurt bowls, dakos-style toast, lentil soup, fasolada, chickpea salad, grilled fish, horta, Greek salads, and olive-oil vegetable sides.

## What Is Included

- `data/foods_catalog.csv`: processed project catalog derived from USDA/FNDDS data
- `data/mediterranean_foods.csv`: curated Mediterranean/Greek extension
- `data/huggingface/food_ranker_items.csv`: export shape for optional hosted dataset browsing

The full USDA archive is not committed. It can be rebuilt through:

```bash
python scripts/build_food_catalog.py
```

## Processing

The data pipeline derives food groups, meal tags, serving sizes, vegetarian flags, vegan flags, and a conservative processing signal. The runtime loader validates the shared schema before recommendation.

## Public-Repo Boundary

The catalog is useful for software ranking and wellness demonstration. It is not a clinical nutrition dataset, allergy database, patient dataset, disease-management dataset, or registered-dietitian validation set.

## Known Limitations

- Some nutrient values come from broad food descriptions rather than exact prepared recipes.
- The curated Mediterranean extension uses estimated USDA-style components.
- Vegan flags are conservative and may exclude ambiguous mixed dishes.
- The catalog does not encode allergies, medications, budget, availability, cooking method, appetite, medical history, or clinician guidance.

## Source Reference

USDA FoodData Central downloadable datasets:

https://fdc.nal.usda.gov/download-datasets/
