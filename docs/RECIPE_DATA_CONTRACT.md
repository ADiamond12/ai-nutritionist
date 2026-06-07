# Recipe Data Contract

## Purpose

This document defines the ingredient-level recipe data milestone for AI Nutritionist: moving from a flat food catalog toward recipe decomposition without pretending that the current repository contains a broad production recipe database.

The current planner is still valid as a general wellness recommender over catalog rows. Some rows are atomic foods, some are meal components, and some are opaque prepared dishes. The repository now includes a tiny fixture-backed validation layer and a five-recipe curated Mediterranean pilot; only those reviewed recipe-backed rows can be expanded into ingredient-level grocery lists.

This is a product/data engineering contract, not medical validation. It must not be used to claim clinical accuracy, allergy safety, guaranteed nutrition adequacy, or therapeutic diet planning.

## Current Boundary

Runtime catalog rows currently use the shared `CATALOG_COLUMNS` schema:

- `fdc_id`
- `food_name`
- `wweia_category`
- `wweia_category_description`
- `food_group`
- `meal_tags`
- `serving_grams`
- `calories`
- `protein_g`
- `carbohydrate_g`
- `fat_g`
- `fiber_g`
- `sugars_g`
- `sodium_mg`
- `saturated_fat_g`
- `vegetarian`
- `vegan`
- `minimally_processed`
- `source`

The recommender, neural ranker, optimizer, public API serialization, and grocery-list export all depend on this row shape. The recipe milestone must preserve this contract during migration by producing recipe-backed rows that can still be projected into the existing catalog schema.

## External Reference Posture

Useful official references:

- USDA FoodData Central downloadable data: https://fdc.nal.usda.gov/download-datasets/
- USDA FoodData Central data type documentation: https://fdc.nal.usda.gov/data-documentation/
- USDA FoodData Central API guide: https://fdc.nal.usda.gov/api-guide
- USDA FoodData Central FAQ: https://fdc.nal.usda.gov/faq/

Design implications for this project:

- FoodData Central has distinct data types with different provenance and serving-size context.
- FNDDS rows are useful for foods reported in What We Eat in America / NHANES, while Foundation Foods and SR Legacy can be useful ingredient references.
- Serving size context is not uniform across all data types, so this project must store source-specific serving basis and its own normalized grams.
- FoodData Central does not automatically modify portion sizes in the downloadable/API data, so portion scaling must remain explicit and deterministic in project code.
- API keys must not be required for public default operation. Any future API-based enrichment must be optional and must not commit keys.

## Contract Files

The implemented layout is:

```text
data/
  recipes/
    recipes.csv
    recipe_ingredients.csv
    recipe_sources.csv
    README.md
tests/
  fixtures/
    recipes/
      recipes.csv
      recipe_ingredients.csv
      recipe_sources.csv
```

The `data/recipes` files are the optional curated recipe pilot layer. The `tests/fixtures/recipes` files are deterministic fixture data for contract tests and should stay tiny, public-safe, and hand-auditable.

No private user feedback, personal health data, private PDFs, ZIP archives, or scraped proprietary recipe text belongs in these files.

## Recipe Entity

`recipes.csv` should contain one row per recipe.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `recipe_id` | string | yes | Stable slug, for example `med_lentil_soup_v1`. Never reuse for materially different ingredients. |
| `recipe_name` | string | yes | Public display name. |
| `description` | string | no | Short neutral description, not marketing or medical copy. |
| `recipe_version` | string | yes | Semantic or date-based version, for example `1.0`. |
| `status` | enum | yes | `fixture`, `draft`, `reviewed`, or `retired`. Public app should default to `reviewed` plus fixture-only tests. |
| `meal_tags` | string list | yes | Comma-separated `breakfast`, `lunch`, `dinner`. |
| `cuisine_tags` | string list | no | Examples: `mediterranean`, `greek`. Culture framing only, not therapy. |
| `dietary_pattern_tags` | string list | yes | Conservative tags such as `omnivore`, `vegetarian`, `vegan`, `keto_style`. |
| `food_group_primary` | enum | yes | One of the current planner groups: `protein`, `vegetable`, `fruit`, `whole_grain`, `healthy_fat`. |
| `servings_per_recipe` | float | yes | Must be greater than zero. |
| `serving_grams` | float | yes | Normalized edible grams per serving. |
| `yield_grams` | float | no | Final cooked/assembled edible yield when known. |
| `yield_basis` | enum | yes | `measured`, `estimated`, `sum_ingredients`, or `unknown`. |
| `prep_time_minutes` | int | no | Optional UX metadata. |
| `cook_time_minutes` | int | no | Optional UX metadata. |
| `cooking_method` | string | no | Examples: `raw`, `boiled`, `grilled`, `baked`, `assembled`. |
| `default_portion_servings` | float | yes | Portion multiplier used when projecting into the flat catalog. |
| `portion_min_servings` | float | yes | Lower bound for optimizer scaling. |
| `portion_max_servings` | float | yes | Upper bound for optimizer scaling. |
| `allergen_tags` | string list | yes | Conservative common-allergen tags derived from ingredients. Empty only when reviewed. |
| `allergen_review_status` | enum | yes | `reviewed`, `uncertain`, or `not_reviewed`. Never use as allergy-safe proof. |
| `dietary_review_status` | enum | yes | `reviewed`, `uncertain`, or `not_reviewed`. |
| `nutrition_review_status` | enum | yes | `reviewed`, `estimated`, or `not_reviewed`. |
| `source_id` | string | yes | Foreign key into `recipe_sources.csv`. |
| `notes` | string | no | Short internal data-quality note. No private or health data. |

## Ingredient Entity

`recipe_ingredients.csv` should contain one row per recipe ingredient.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `recipe_id` | string | yes | Foreign key to `recipes.csv`. |
| `ingredient_id` | string | yes | Stable row ID unique inside a recipe. |
| `ingredient_name` | string | yes | Plain ingredient display name. |
| `ingredient_role` | enum | yes | `protein`, `vegetable`, `fruit`, `whole_grain`, `healthy_fat`, `seasoning`, `liquid`, or `other`. |
| `fdc_id` | int/string | no | FoodData Central ID when mapped. Blank only for curated estimates or fixture rows. |
| `fdc_data_type` | enum | no | `FNDDS`, `Foundation`, `SR Legacy`, `Branded`, `curated`, or `fixture`. |
| `source_food_name` | string | no | Source food description used for nutrient mapping. |
| `quantity` | float | yes | Human recipe quantity before normalization. |
| `unit` | string | yes | `g`, `ml`, `cup`, `tbsp`, `tsp`, `piece`, etc. |
| `edible_grams` | float | yes | Normalized edible grams used for nutrient aggregation. |
| `preparation_state` | string | no | Examples: `raw`, `cooked`, `drained`, `canned_rinsed`. |
| `nutrient_basis` | enum | yes | `per_100g`, `per_source_serving`, or `estimated`. |
| `is_optional` | bool | yes | Optional garnish/substitution ingredients should not be required for baseline nutrition. |
| `substitution_group` | string | no | Stable group for future swaps, for example `legume_base`. |
| `vegetarian` | bool | yes | Conservative ingredient-level flag. |
| `vegan` | bool | yes | Conservative ingredient-level flag. |
| `contains_allergen_tags` | string list | yes | Conservative tags, blank only after review. |
| `mapping_confidence` | enum | yes | `exact`, `close`, `estimated`, or `fixture`. |
| `mapping_notes` | string | no | Short data-quality note. |
| `calories_per_100g` | float | yes for required ingredients | Source calories normalized to 100g. |
| `protein_g_per_100g` | float | yes for required ingredients | Source protein normalized to 100g. |
| `carbohydrate_g_per_100g` | float | yes for required ingredients | Source carbohydrate normalized to 100g. |
| `fat_g_per_100g` | float | yes for required ingredients | Source fat normalized to 100g. |
| `fiber_g_per_100g` | float | yes for required ingredients | Source fiber normalized to 100g. |
| `sugars_g_per_100g` | float | yes for required ingredients | Source total sugars normalized to 100g. |
| `sodium_mg_per_100g` | float | yes for required ingredients | Source sodium normalized to 100g. |
| `saturated_fat_g_per_100g` | float | yes for required ingredients | Source saturated fat normalized to 100g. |

## Source Entity

`recipe_sources.csv` should store source and licensing metadata.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `source_id` | string | yes | Stable key referenced by `recipes.csv`. |
| `source_type` | enum | yes | `usda_fdc`, `curated_estimate`, `fixture`, or another reviewed type. |
| `source_title` | string | yes | Human-readable source label. |
| `source_url` | string | no | Public URL when available. |
| `source_release` | string | no | Example: `FNDDS 2021-2023, October 2024 release`. |
| `source_license` | string | yes | Public-domain/source posture where known. |
| `created_by` | string | no | Use project/team role, not private personal data. |
| `created_at` | date | yes | ISO date. |
| `reviewed_at` | date | no | ISO date when reviewed. |
| `review_notes` | string | no | Non-sensitive provenance note. |

## Nutrition Aggregation Rules

The recipe layer must aggregate nutrients deterministically before projecting recipes into the existing flat catalog.

Required nutrient keys:

- `calories`
- `protein_g`
- `carbohydrate_g`
- `fat_g`
- `fiber_g`
- `sugars_g`
- `sodium_mg`
- `saturated_fat_g`

Rules:

1. Normalize each ingredient to `edible_grams`.
2. Convert source nutrients to a common per-gram basis.
3. Compute ingredient contribution as `source_value_per_100g * edible_grams / 100`.
4. Sum ingredient contributions using full precision.
5. Compute per-serving nutrients as `recipe_total / servings_per_recipe`.
6. Set projected `serving_grams` to `yield_grams / servings_per_recipe` when `yield_basis` is `measured` or `estimated`; otherwise use `sum(edible_grams) / servings_per_recipe` and set `yield_basis=sum_ingredients`.
7. Round public catalog nutrients to one decimal at the final projection boundary, matching current catalog behavior.
8. Do not apply cooking-loss or retention factors unless a source-backed retention table is explicitly added and tested later.
9. If any required nutrient is missing for a non-optional ingredient, mark the recipe `nutrition_review_status=not_reviewed` and exclude it from production recommendations.
10. Portion scaling must use the same scalable keys as the current optimizer: grams, calories, protein, carbohydrate, fat, fiber, sugars, sodium, and saturated fat.

## Dietary Pattern Validation

Dietary tags must be derived from ingredients, not hand-waved from recipe names.

Rules:

- `vegan` requires every required ingredient to be conservatively vegan.
- `vegetarian` requires every required ingredient to be conservatively vegetarian.
- Ambiguous ingredients fail closed: they should produce `dietary_review_status=uncertain` and should not get vegan/vegetarian tags until reviewed.
- `mediterranean` / `greek` are cuisine or food-culture tags, not medical diet claims.
- `keto_style` remains a low-carbohydrate wellness filter, not a therapeutic ketogenic diet. It should require carbohydrate checks against project thresholds and saturated-fat guardrails.
- Optional ingredients must be modeled explicitly. A non-vegan optional topping must not make the baseline recipe vegan unless the public recipe rendering clearly excludes that topping from the vegan version.

## Sodium Validation

Sodium remains a product guardrail, not a medical sodium prescription.

Rules:

- Aggregate sodium from ingredient-level source values.
- Preserve sodium per serving in the projected flat catalog row.
- Flag high-sodium recipes during review using the same daily and meal guardrail context already used by the planner.
- If sodium is missing for any required ingredient, exclude the recipe from production recommendations until reviewed.
- Do not label recipes as `low sodium` unless a separate labeling policy is added and verified. Current UI should prefer neutral language such as planning notes or guardrail warnings.

## Allergen Validation

The project must not claim allergy safety.

Rules:

- Track common-allergen tags at ingredient and recipe level: `milk`, `egg`, `fish`, `shellfish`, `tree_nut`, `peanut`, `wheat_gluten`, `soy`, and `sesame`.
- Recipe-level tags are the union of ingredient-level tags.
- If an ingredient is ambiguous, mark `allergen_review_status=uncertain`.
- Public copy must say allergen tags are informational product metadata only, not a guarantee.
- User avoid/prefer terms are not allergy controls.
- No recipe with `allergen_review_status=uncertain` should be presented as allergy-friendly.

## Projection Into Current Catalog

The first implementation should not rewrite the recommender. It should add a projection step that converts reviewed recipe rows into the existing catalog schema.

Projection mapping:

- `fdc_id`: use a reserved internal numeric range or a stable string-to-number mapping for curated recipe rows.
- `food_name`: `recipe_name`.
- `wweia_category`: reserved curated recipe category code.
- `wweia_category_description`: `Curated ingredient-level recipe`.
- `food_group`: `food_group_primary`.
- `meal_tags`: copied from recipe.
- `serving_grams`: projected per-serving grams.
- nutrient columns: aggregated per-serving nutrients.
- `vegetarian` / `vegan`: derived from dietary validation.
- `minimally_processed`: conservative derived flag; default false unless ingredient roles and source review justify true.
- `source`: include source label and recipe contract version.

This preserves current ranker/planner behavior while making ingredient details available to future UI/API layers.

## Migration Path

Phase 0: Contract only - complete

- Add this document.
- Keep current recommender behavior unchanged.

Phase 1: Fixture schema and pure aggregation - complete

- Add tiny deterministic fixture CSVs under `tests/fixtures/recipes`.
- Implement schema validation and nutrient aggregation functions.
- Test per-serving nutrient math, missing-nutrient rejection, dietary flag derivation, allergen union, and projection into `CATALOG_COLUMNS`.

Phase 2: Curated Mediterranean recipe pilot - implemented as a small reviewed pilot

- Add a small number of reviewed recipe-backed Mediterranean entries under `data/recipes`.
- Keep original flat rows available.
- Treat recipe-pilot nutrients as curated estimates and document that this is not a broad production recipe corpus.

Phase 3: Runtime integration - partial

- Add optional loader support for recipe-backed projected rows.
- Keep the public default deterministic and local.
- Expose ingredient-level grocery lists only for selected recipe-backed meals.
- Preserve current public API score-hiding behavior.

Phase 4: Reviewer proof - ongoing

- Add tests for recipe-backed recommendations, grocery-list ingredient grouping, dietary filters, and public payload shape.
- Refresh docs/screenshots only after verified UI behavior exists.
- Do not claim clinical accuracy or allergy safety.

## Deterministic Test Fixture Strategy

Use fixtures that are small, stable, and obviously non-private.

Recommended fixture recipes:

- `fixture_lentil_soup_v1`: vegan legume soup with lentils, tomato, carrot, onion, olive oil, water, and salt.
- `fixture_greek_yogurt_bowl_v1`: vegetarian breakfast with yogurt, berries, oats, and walnuts; must carry `milk` and `tree_nut` allergen tags and must not be vegan.
- `fixture_chicken_rice_plate_v1`: omnivore lunch/dinner with chicken, rice, vegetables, olive oil, and salt.

Initial contract tests should verify:

- required recipe, ingredient, and source columns;
- positive `servings_per_recipe`, `serving_grams`, and `edible_grams`;
- deterministic nutrient aggregation from fixture ingredients;
- sodium aggregation and rejection when sodium is missing;
- vegan and vegetarian derivation from ingredient flags;
- allergen union behavior;
- projection output contains every `CATALOG_COLUMNS` field;
- projected recipe rows do not expose private notes or internal review metadata in public API payloads.

Do not add placeholder tests that assert future broad recipe files exist before the implementation plan is approved.

## Acceptance Gates For The Next Implementation PR

Changes to this recipe layer should pass:

- `ruff check .`
- `mypy ai_nutritionist`
- `pytest -q`
- `python -m ai_nutritionist.evaluation`
- daily and weekly CLI smoke tests
- tracked artifact scan
- tracked secret-pattern scan

Additional recipe-specific acceptance gates:

- no private data, PDFs, ZIPs, feedback exports, or secrets committed;
- no API key requirement for public default runs;
- recipe-backed projection is deterministic for the same code and data;
- existing flat catalog loader remains backward compatible;
- current public API payloads continue to hide internal ranking and optimizer scores;
- docs describe recipe data as a data-engineering milestone, not clinical validation.

## Non-Goals

- No broad production recipe corpus in this milestone.
- No scraping proprietary recipe websites.
- No user-generated recipe persistence.
- No clinical meal-plan validation.
- No allergy-safe claims.
- No therapeutic keto claims.
- No hosted-demo claims from the recipe layer. Docker-runtime claims must be separately verified outside the recipe data contract.
- No mandatory OpenAI, USDA API, or paid-provider dependency.
