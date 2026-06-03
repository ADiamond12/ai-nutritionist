# AI Nutritionist

[![CI](https://github.com/ADiamond12/ai-nutritionist/actions/workflows/ci.yml/badge.svg)](https://github.com/ADiamond12/ai-nutritionist/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.50%2B-red)

AI Nutritionist is a local-first nutrition recommendation system that builds profile-aware daily and weekly meal plans from USDA FoodData Central / FNDDS data plus a curated Mediterranean/Greek food extension. The current version uses an expanded processed catalog, conservative dietary filters, a deterministic neural MLP food ranker, explicit weight-goal controls, and constraint-based meal assembly.

This is not a medical or clinical tool. It provides general wellness nutrition suggestions only and should not be used to diagnose, treat, or manage any health condition.

## Project Status

The public version is a standalone software system, not a thesis, dissertation, or academic submission. It evolved from an earlier recommender prototype into a portfolio-ready application with a reproducible data pipeline, neural ranking, CLI, Streamlit UI, tests, and evaluation notes.

## Public Artifacts

- [MODEL_CARD.md](MODEL_CARD.md) explains the weak-label neural ranker, deterministic guardrails, and non-clinical boundary.
- [DATA_CARD.md](DATA_CARD.md) explains the USDA/FNDDS-derived catalog, curated Mediterranean extension, and data limitations.
- [docs/EVALUATION.md](docs/EVALUATION.md) records the runnable product-quality evaluation matrix.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) outlines package modules, data flow, ranking, and feedback handling.
- [docs/deployment/STREAMLIT_COMMUNITY_CLOUD.md](docs/deployment/STREAMLIT_COMMUNITY_CLOUD.md) and [docs/deployment/huggingface-space-README.md](docs/deployment/huggingface-space-README.md) document hosted deployment setup.
- [SECURITY.md](SECURITY.md) documents supported reporting and the local-first privacy boundary.

## Reviewer Proof

- **Problem:** meal-planning demos often stop at a recommendation list; this project adds profile-aware constraints, nutrition targets, data cards, model notes, and repeatable tests.
- **First command:** `streamlit run app.py`
- **Proof artifact:** generated daily and weekly meal-plan screenshots under `docs/screenshots/`.
- **Visual proof:** start with `docs/screenshots/streamlit-meal-plan.png`, then show weekly rotation, daily nutrition progress, and swap alternatives.
- **Validation:** 59 pytest tests, Docker health check, BMI/age/diet evaluation matrix, CLI/API smoke tests, lint/type automation, and Streamlit smoke testing.
- **Current limitation:** this is a general wellness software demo, not medical advice or clinical decision support.

## What It Does

- Calculates BMI and a coarse BMI category from height and weight.
- Estimates daily energy, protein, fiber, sodium, saturated-fat, and sugar guardrails from profile inputs.
- Separates weight goal (`auto`, maintain, lose, gain) from nutrition focus (`balanced`, higher protein, higher fiber, lighter meals, lower sodium).
- Uses a bounded calorie deficit for explicit weight-loss plans and scales portions when a generated plan sits too far above the target.
- Optionally uses body-fat percentage to estimate lean body mass and raise protein targets.
- Builds an expanded processed USDA/FNDDS food catalog with meal tags, serving sizes, vegetarian flags, vegan flags, and processing signals.
- Adds a curated Mediterranean/Greek extension with practical foods such as Greek yogurt bowls, dakos-style toast, lentil soup, fasolada, chickpea salads, grilled fish, horta, Greek salads, and olive-oil vegetable sides.
- Trains a deterministic `MLPRegressor` ranker on weak-supervised nutrition-quality labels derived from USDA nutrients and public-health guidance.
- Combines neural ranking with hard meal guardrails for calories, sodium, saturated fat, sugars, and food-family repetition.
- Supports nutrition focus modes: balanced, higher protein, higher fiber, lighter meals, and lower sodium.
- Supports avoid/prefer terms so users can steer recommendations without making medical claims.
- Supports Mediterranean/Greek, omnivore, vegetarian, vegan, and keto-style / low-carb dietary patterns.
- Builds a 7-day plan option with Mediterranean-style rotation across poultry, fish/seafood, legumes, vegetables, whole grains/starches, and olive-oil sides.
- Produces meal titles, item-level nutrient totals, macro percentages, daily progress, swap alternatives, local thumbs feedback, and plain-language explanations.
- Produces grouped grocery lists with CSV export for daily or weekly plans.
- Exposes a FastAPI app with public-safe daily and weekly recommendation payloads that hide internal ranking scores.
- Stores feedback only in the current Streamlit session by default; it can be exported as CSV, but it is not uploaded by the app.
- Supports an optional local SQLite feedback store for API experiments. The default path is `.local/feedback.sqlite`, which is ignored by git.

## Screenshots

Screenshots live under `docs/screenshots/` and are kept in the repository so reviewers can understand the app before running Streamlit locally.

| Generated meal plan | Weekly rotation |
| --- | --- |
| ![AI Nutritionist generated meal plan](docs/screenshots/streamlit-meal-plan.png) | ![AI Nutritionist weekly meal rotation](docs/screenshots/streamlit-weekly-plan.png) |

| Daily nutrition progress | Swap alternatives |
| --- | --- |
| ![AI Nutritionist daily nutrition progress](docs/screenshots/streamlit-daily-nutrition.png) | ![AI Nutritionist swap alternatives](docs/screenshots/streamlit-alternatives.png) |

Recommended capture flow:

```bash
streamlit run app.py
```

Open the local Streamlit URL, generate recommendations, and save screenshots as:

- `docs/screenshots/streamlit-meal-plan.png`
- `docs/screenshots/streamlit-weekly-plan.png`
- `docs/screenshots/streamlit-daily-nutrition.png`
- `docs/screenshots/streamlit-alternatives.png`
- `docs/screenshots/streamlit-mobile-day-detail.png`

## Setup

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

For development checks:

```bash
python -m pip install -e .[dev]
```

## Streamlit Usage

```bash
streamlit run app.py
```

The Streamlit app requires the user to press `Generate meal plan` before recommendations appear. After generation, users can leave thumbs feedback for the full plan or individual meals. Negative feedback is stored locally in `st.session_state` and can be used by `Regenerate with feedback` as a temporary avoid signal for the next plan.

## CLI Usage

```bash
ai-nutritionist --weight 75 --height 180 --age 30 --sex male --activity moderate --dietary-pattern mediterranean --weight-goal maintain --top-k 4
```

Preference-aware example:

```bash
ai-nutritionist --weight 75 --height 180 --age 30 --goal-focus lower_sodium --avoid "fish,chicken" --prefer "beans" --top-k 4
```

Weekly Mediterranean example:

```bash
ai-nutritionist --weight 125 --height 200 --age 30 --sex male --activity moderate --dietary-pattern mediterranean --weight-goal lose --weekly --top-k 3
```

Vegan example:

```bash
ai-nutritionist --weight 68 --height 172 --age 32 --sex female --activity moderate --dietary-pattern vegan --top-k 4
```

Keto-style example:

```bash
ai-nutritionist --weight 75 --height 180 --age 30 --dietary-pattern keto_style --body-fat 18 --goal-focus higher_protein --top-k 4
```

`python cli.py ...` remains available for direct source-checkout runs.

Options:

- `--weight`: weight in kg
- `--height`: height in cm
- `--age`: age in years
- `--sex`: `female`, `male`, or `unspecified`
- `--activity`: `sedentary`, `light`, `moderate`, or `active`
- `--dietary-pattern`: `mediterranean`, `omnivore`, `vegetarian`, `vegan`, or `keto_style`
- `--weight-goal`: `auto`, `maintain`, `lose`, or `gain`
- `--body-fat`: optional body-fat percentage used for a lean-mass protein target
- `--goal-focus`: `balanced`, `higher_protein`, `higher_fiber`, `lighter_meals`, or `lower_sodium`
- `--avoid`: comma-separated food-name terms to exclude
- `--prefer`: comma-separated food-name terms to boost
- `--top-k` / `--topk`: number of foods per meal, minimum 3
- `--weekly`: build a weekly plan instead of one day
- `--days`: number of days for weekly mode, from 1 to 14

## API Usage

```bash
ai-nutritionist-api
```

The API runs on `http://127.0.0.1:8000` by default. Open `http://127.0.0.1:8000/docs` for the generated OpenAPI UI.

Daily recommendation smoke request:

```bash
python -c "from fastapi.testclient import TestClient; from ai_nutritionist.api import create_app; c=TestClient(create_app()); print(c.post('/recommend/daily', json={'weight_kg':75,'height_cm':180,'age':30,'sex':'male','dietary_pattern':'mediterranean'}).json()['daily_targets']['calories'])"
```

The public API response includes plan data, nutrition totals, alternatives, and grocery lists. It intentionally excludes internal model scores and is still a wellness recommender, not medical advice.

## Docker

```bash
docker build -t ai-nutritionist .
docker run --rm -p 8501:8501 ai-nutritionist
```

The container starts Streamlit on `0.0.0.0:8501` and exposes the standard Streamlit health endpoint.

## Deployment Notes

The repository is ready for local, Docker, Streamlit Community Cloud, or Hugging Face Spaces deployment. A hosted deployment is optional because the app handles profile inputs and local feedback. When deployed remotely, user profile inputs are processed by the hosting platform rather than only on the user's machine.

For Streamlit Community Cloud, point the app to `app.py` and install from `requirements.txt`; see [docs/deployment/STREAMLIT_COMMUNITY_CLOUD.md](docs/deployment/STREAMLIT_COMMUNITY_CLOUD.md). For Hugging Face Spaces, use a Streamlit Space with `app.py` as the entry point and the committed CSV data files included in the repository; see [docs/deployment/huggingface-space-README.md](docs/deployment/huggingface-space-README.md). No API keys or private model files are required.

## Data

The committed base catalog at `data/foods_catalog.csv` is derived from USDA FoodData Central FNDDS 2021-2023 CSV data, release date October 2024. `data/mediterranean_foods.csv` adds a small curated Mediterranean/Greek extension with estimated nutrient values from USDA-style food components so the public app recommends recognizable meals rather than isolated high-scoring ingredients. The full USDA archive is not committed.

The current combined export contains 2,049 rows: 2,014 USDA/FNDDS-derived rows plus 35 curated Mediterranean/Greek rows. See [DATA_CARD.md](DATA_CARD.md) for provenance, schema, source posture, and known limitations.

Rebuild the processed catalog and Hugging Face-compatible CSV export:

```bash
python scripts/build_food_catalog.py
```

Source: https://fdc.nal.usda.gov/download-datasets/

The vegan classifier is conservative: ambiguous mixed dishes are not marked vegan unless category and description rules make plant-only status clear enough for a public wellness recommender. Mediterranean/Greek mode is food-culture framing, not a medical diet prescription. Keto-style mode is a low-carbohydrate wellness filter, not a therapeutic ketogenic diet.

## Neural Ranking

The project does not claim clinical fine-tuning. Instead, it trains a lightweight scikit-learn MLP ranker on weak labels generated from the local USDA catalog: nutrient density, meal fit, sodium, saturated fat, total sugars, processing signal, and BMI-aware energy direction. This gives the project a reproducible local ML component while staying honest about the absence of clinical outcome labels.

See [MODEL_CARD.md](MODEL_CARD.md) for model type, weak-label strategy, input features, evaluation boundary, safety posture, and failure modes.

The weekly planner is deterministic orchestration around the same ranker and guardrails. It rotates preference boosts by day so Mediterranean mode can produce practical chicken, fish, legumes, vegetables, whole grains/starches, yogurt, and olive-oil side patterns rather than repeating one high-scoring day.

## Evaluation

The project includes an evaluation matrix across underweight, normal, overweight, severely overweight, older-adult, Mediterranean, vegetarian, vegan, and keto-style profiles.

```bash
python -m ai_nutritionist.evaluation
```

See [docs/EVALUATION.md](docs/EVALUATION.md) and [docs/RESEARCH.md](docs/RESEARCH.md). The matrix reports calorie-target fit and a transparent constraint-only baseline proxy. It is a product-quality and guidance-alignment smoke test, not clinical validation.

## Tests

```bash
ruff check .
mypy ai_nutritionist
pytest -q
```

Coverage includes BMI/category logic, explicit weight goals, bounded weight-loss calorie targets, body-fat protein targets, macro totals, USDA catalog schema, Mediterranean extension loading, neural ranking reproducibility, vegan filtering, keto-style filtering, preference-aware ranking, recommendation shape, weekly Mediterranean rotation, grocery-list output, public API payloads, local feedback UI contracts, optional local feedback storage, alternatives, practical meal constraints, evaluation matrix behavior, and CLI smoke behavior.

## Privacy And Security

Local runs do not upload profile inputs, generated plans, or feedback. Streamlit feedback is stored in `st.session_state` only unless the user downloads a CSV. API feedback experiments can use a local SQLite file under `.local/`, which is ignored by git. Treat exported CSVs and local feedback databases as user data and avoid committing them.

Do not enter sensitive medical details, diagnoses, medication information, allergy-critical requirements, or private health records. For security reporting and supported boundaries, see [SECURITY.md](SECURITY.md).

## Limitations

- BMI is a simplified population-level indicator and is not a diagnosis.
- Energy targets are estimates based on profile assumptions, not clinical prescriptions.
- Weight-loss targets use a bounded deficit heuristic and portion scaling, but they do not guarantee weight change.
- Feedback is local product feedback, not a clinical outcome label or diagnosis signal.
- USDA nutrient rows and curated Mediterranean estimates are useful reference data but do not capture allergies, medication interactions, budget, cooking method, appetite, disease state, or clinician guidance.
- Total sugars are not the same as added sugars. The system treats sugar as a ranking and guardrail signal, not a medical rule.
- Vegan recommendations include plant-only filtering but do not solve B12, vitamin D, iron, iodine, omega-3, or calcium planning by themselves.
- Keto-style recommendations are not a therapeutic ketogenic diet and should not be used to manage diabetes, epilepsy, pregnancy nutrition, or medical conditions.
- The neural ranker is trained on weak labels, not clinical outcomes or registered-dietitian preference labels.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
