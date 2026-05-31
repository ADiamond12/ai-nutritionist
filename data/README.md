# Nutrition Data

`foods_catalog.csv` is a processed project catalog derived from the USDA FoodData Central FNDDS 2021-2023 CSV release dated October 2024.

`mediterranean_foods.csv` is a curated Mediterranean/Greek extension with practical meal rows such as Greek yogurt bowls, dakos-style toast, lentil soup, fasolada, chickpea salad, grilled fish, horta, Greek salads, and olive-oil vegetable sides. Nutrients are estimated from USDA-style components and are intended for software ranking and wellness demonstrations, not clinical dietetics.

The full USDA download is intentionally not committed. Rebuild the processed catalog and Hugging Face-compatible export with:

```bash
python scripts/build_food_catalog.py
```

Source: https://fdc.nal.usda.gov/download-datasets/

The runtime loader merges both CSVs, then validates the shared schema. The catalog includes derived food groups, meal tags, serving sizes, vegetarian flags, vegan flags, and a conservative processing signal. These fields are designed for a general wellness recommender and do not establish clinical suitability for any individual.
