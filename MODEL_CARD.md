# Model Card

## Model Purpose

AI Nutritionist uses a local scikit-learn `MLPRegressor` as a food-ranking component inside a deterministic meal planner. The model ranks catalog rows for general wellness meal assembly. It does not diagnose, treat, or manage health conditions.

## Training Signal

The ranker is trained on weak labels generated from project rules over the local USDA/FNDDS-derived food catalog. The weak labels reward nutrient density, meal fit, lower sodium density, lower saturated fat density, lower total sugar density, and a minimally processed signal.

The model is not clinical. It is not trained on registered-dietitian decisions, medical records, disease outcomes, allergy profiles, medication interactions, or patient histories.

## System Boundary

The model does not produce meal plans by itself. The planner combines its ranking score with deterministic guardrails for:

- meal slot fit
- dietary-pattern filters
- calorie range
- protein and fiber presence
- sodium, saturated fat, and sugar limits
- food-family repetition
- user avoid and prefer terms

## Evaluation

The repository includes a product-quality evaluation matrix in `docs/EVALUATION.md` and a runnable smoke command:

```bash
python -m ai_nutritionist.evaluation
```

The evaluation checks structural behavior across profile and dietary-pattern cases. It should not be read as clinical validation.

## Limitations

- BMI and energy estimates are simplified planning inputs.
- Total sugar values are not equivalent to added sugar values.
- Vegan and keto-style modes are conservative software filters, not medical diet plans.
- The ranker can surface odd food combinations, so deterministic meal guardrails remain required.
- The app is intended for local portfolio demonstration and general wellness exploration only.
