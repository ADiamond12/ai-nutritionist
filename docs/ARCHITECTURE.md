# Architecture

AI Nutritionist is a local-first nutrition recommendation system built around a processed USDA FoodData Central catalog, a curated Mediterranean/Greek extension, deterministic neural ranking, explicit weight-goal controls, weekly rotation, local feedback capture, and constraint-based meal assembly.

## Project Status

This repository is maintained as a standalone public software project. It is not presented as a thesis, dissertation, or academic deliverable. The current architecture replaces the earlier prototype shape with a clearer package structure, reproducible USDA data preparation, neural ranking, practical meal constraints, and documented evaluation.

## Entry Points

- `app.py`: Streamlit UI for profile input, meal-plan review, local thumbs feedback, and feedback CSV export.
- `cli.py`: command-line wrapper for reproducible runs.

## Package Modules

- `ai_nutritionist.data`: path-safe catalog loading and schema validation.
- `ai_nutritionist.metrics`: BMI/category logic and legacy macro helpers.
- `ai_nutritionist.profile`: energy, bounded explicit weight-goal, lean-mass-aware protein, fiber, sodium, saturated-fat, and sugar target estimation.
- `ai_nutritionist.scoring`: deterministic weak-label scoring used for model training and fallback ranking.
- `ai_nutritionist.preferences`: goal-focus parsing, avoid/prefer term handling, and score adjustments.
- `ai_nutritionist.ranker`: cached neural MLP training and prediction.
- `ai_nutritionist.recommender`: dietary filtering, daily and weekly meal assembly, guardrails, quality scoring, alternatives, and explanations.
- `ai_nutritionist.evaluation`: BMI/age/dietary-pattern evaluation matrix.
- `ai_nutritionist.cli`: ASCII-safe command-line rendering.

## Data Flow

1. `scripts/build_food_catalog.py` downloads or reads the USDA FNDDS ZIP archive.
2. The builder joins food descriptions, WWEIA categories, nutrients, and derived serving rules.
3. The processed catalog is written to `data/foods_catalog.csv` and mirrored to `data/huggingface/food_ranker_items.csv`.
4. Runtime loading validates the catalog schema, merges `data/mediterranean_foods.csv` when present, and converts numeric and boolean fields.
5. A `NutritionProfile` is built from weight, height, age, sex, activity, explicit weight goal, and optional body-fat percentage.
6. The neural ranker trains once per process from weak-supervised labels and is cached.
7. Candidate foods are filtered by dietary pattern, meal tags, vegan/vegetarian/keto-style rules, meal context, and user avoid terms.
8. Goal focus, Mediterranean practicality boosts, low-practicality garnish penalties, and preferred terms adjust ranking while the planner still enforces hard guardrails.
9. Explicit weight-loss targets use a bounded deficit heuristic, then generated meals can be portion-scaled when they sit above the energy target.
10. The planner assembles each meal from protein, produce, grain/starch, and healthy-fat slots while avoiding repeated food families, repeated dish terms, and guardrail violations.
11. Daily mode returns structured items, daily totals, macro percentages, progress metrics, grouped alternatives, model metadata, and explanations. Internal quality scores remain available for tests and evaluation, but are not shown in the customer-facing UI.
12. Weekly mode calls the same recommender through deterministic rotation terms. Mediterranean mode rotates poultry, fish/seafood, legumes, vegetables, whole grains/starches, yogurt, and olive-oil sides so the output behaves more like a practical week plan than a repeated single-day result.
13. The Streamlit UI records thumbs feedback only in local `st.session_state`. Negative feedback can become temporary avoid terms for `Regenerate with feedback`, and the session log can be exported as CSV.

## Data Provenance

`data/foods_catalog.csv` is generated from the USDA FoodData Central FNDDS 2021-2023 CSV release dated October 2024. `data/mediterranean_foods.csv` is a curated extension with practical Mediterranean/Greek meal rows and estimated nutrients from USDA-style components. The full USDA archive is not committed.

## Neural Model

The model is a scikit-learn `MLPRegressor` trained locally on weak labels derived from public nutrient data and guidance-alignment rules. This is a real neural model, but it is not clinical fine-tuning and is not trained on patient outcomes.

## Safety Posture

The system provides general wellness nutrition suggestions only. It is not medical advice, does not diagnose or treat conditions, and avoids claims of clinical accuracy.

Feedback is intentionally local-first. The app does not upload feedback, profile data, or generated plans to a remote service.
