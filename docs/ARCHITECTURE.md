# Architecture

AI Nutritionist is a local-first nutrition recommendation system built around a processed USDA FoodData Central catalog, a curated Mediterranean/Greek extension, deterministic neural ranking, Hybrid V2 complete-day optimization, explicit weight-goal controls, weekly rotation, local feedback capture, and guarded meal assembly.

## Project Status

This repository is maintained as a standalone public software project. It is not presented as a thesis, dissertation, or academic deliverable. The current architecture replaces the earlier prototype shape with a clearer package structure, reproducible USDA data preparation, neural ranking, practical meal constraints, and documented evaluation.

## Entry Points

- `app.py`: Streamlit UI for profile input, meal-plan review, local thumbs feedback, and feedback CSV export.
- `cli.py`: command-line wrapper for reproducible runs.
- `ai_nutritionist.api`: FastAPI app for public-safe daily/weekly recommendation payloads and optional local feedback experiments.

## Package Modules

- `ai_nutritionist.data`: path-safe catalog loading, schema validation, Mediterranean extension merging, and optional recipe-backed projection.
- `ai_nutritionist.recipes`: recipe/source/ingredient contract loading, validation, nutrient aggregation, flat catalog projection, and ingredient grocery helpers.
- `ai_nutritionist.metrics`: BMI/category logic and legacy macro helpers.
- `ai_nutritionist.profile`: energy, bounded explicit weight-goal, lean-mass-aware protein, fiber, sodium, saturated-fat, and sugar target estimation.
- `ai_nutritionist.scoring`: deterministic weak-label scoring used for model training and fallback ranking.
- `ai_nutritionist.preferences`: goal-focus parsing, avoid/prefer term handling, and score adjustments.
- `ai_nutritionist.ranker`: cached neural MLP training and prediction.
- `ai_nutritionist.recommender`: dietary filtering, daily and weekly meal assembly, guardrails, quality scoring, alternatives, and explanations.
- `ai_nutritionist.optimizer`: deterministic complete-day optimization, bounded substitutions/portions, hard-limit preservation, and public-safe planning notes.
- `ai_nutritionist.presentation`: public response serialization that removes internal ranking fields from API-facing payloads.
- `ai_nutritionist.plan_outputs`: grouped grocery-list builders, recipe ingredient grocery bridge, and CSV export helpers for generated plans.
- `ai_nutritionist.feedback`: optional local SQLite feedback storage for API experiments.
- `ai_nutritionist.evaluation`: BMI/age/dietary-pattern evaluation matrix.
- `ai_nutritionist.cli`: ASCII-safe command-line rendering.

## Data Flow

1. `scripts/build_food_catalog.py` downloads or reads the USDA FNDDS ZIP archive.
2. The builder joins food descriptions, WWEIA categories, nutrients, and derived serving rules.
3. The processed catalog is written to `data/foods_catalog.csv` and mirrored to `data/huggingface/food_ranker_items.csv`.
4. Runtime loading validates the catalog schema, merges `data/mediterranean_foods.csv` when present, projects reviewed `data/recipes/` rows into the same catalog schema, and converts numeric and boolean fields.
5. A `NutritionProfile` is built from weight, height, age, sex, activity, explicit weight goal, and optional body-fat percentage.
6. The neural ranker trains once per process from weak-supervised labels and uses a single-entry in-process cache to avoid retaining multiple fitted pipelines in long-running deployments.
7. Candidate foods are filtered by dietary pattern, meal tags, vegan/vegetarian/keto-style rules, meal context, and user avoid terms.
8. Goal focus, Mediterranean practicality boosts, low-practicality garnish penalties, and preferred terms adjust ranking while the planner still enforces hard guardrails.
9. Explicit weight-loss targets use a bounded deficit heuristic, then generated meals can be portion-scaled when they sit above the energy target.
10. The planner assembles each meal from protein, produce, grain/starch, and healthy-fat slots while avoiding repeated food families, repeated dish terms, and guardrail violations.
11. Hybrid V2 evaluates the complete daily plan and performs deterministic, bounded same-group substitutions and portion adjustments. It preserves already-passing hard limits and accepts only objective-improving changes.
12. Daily mode returns structured items, daily totals, macro percentages, progress metrics, grouped alternatives, planner diagnostics, and explanations. Internal ranking and optimization scores are not shown in the customer-facing UI or public API payloads.
13. Weekly mode calls the same recommender through deterministic rotation terms. Mediterranean mode rotates poultry, fish/seafood, legumes, vegetables, whole grains/starches, yogurt, and olive-oil sides so the output behaves more like a practical week plan than a repeated single-day result.
14. `plan_outputs` groups generated daily or weekly catalog items into a grocery list and CSV export. When selected foods match reviewed recipe-backed rows, it can also produce ingredient-level grocery rows without exposing internal recipe metadata in the public meal items.
15. The Streamlit UI records thumbs feedback only in local `st.session_state`. Negative feedback can become temporary avoid terms for `Regenerate with feedback`, and the session log can be exported as CSV.
16. The FastAPI layer serializes public-safe payloads through `presentation`, exposes a health check and OpenAPI docs, and initializes the ignored local SQLite feedback store only when local feedback endpoints are used.

## Data Provenance

`data/foods_catalog.csv` is generated from the USDA FoodData Central FNDDS 2021-2023 CSV release dated October 2024. `data/mediterranean_foods.csv` is a curated extension with practical Mediterranean/Greek meal rows and estimated nutrients from USDA-style components. `data/recipes/` is a five-recipe ingredient-level pilot with curated-estimate nutrients, source metadata, and review fields. The full USDA archive is not committed.

## Neural Model

The model is a scikit-learn `MLPRegressor` trained locally on weak labels derived from public nutrient data and guidance-alignment rules. This is a real neural model, but it is not clinical fine-tuning and is not trained on patient outcomes.

## Hybrid V2 Planner

The default planner retains the neural ranker as candidate generation and adds deterministic coordinate-search optimization across the assembled day. The legacy planner remains selectable for paired evaluation. The optimizer is a software heuristic, not clinical optimization.

Most catalog rows can represent atomic foods, components, or opaque prepared dishes. The planner treats them as plate compositions by default. The reviewed recipe-backed pilot can be expanded into ingredient grocery rows, but the project does not claim a broad validated recipe database.

[RECIPE_DATA_CONTRACT.md](RECIPE_DATA_CONTRACT.md) keeps the flat catalog projection as the compatibility boundary while specifying recipe, ingredient, source, nutrition aggregation, sodium, allergen, dietary validation, fixture tests, and migration expectations.

## Safety Posture

The system provides general wellness nutrition suggestions only. It is not medical advice, does not diagnose or treat conditions, and avoids claims of clinical accuracy.

Feedback is intentionally local-first. The Streamlit app does not upload feedback, profile data, or generated plans to a remote service. The optional API feedback store is created lazily from feedback endpoints and writes only to a local SQLite path such as `.local/feedback.sqlite`, which is not committed.
