# Evaluation

The evaluation matrix checks whether the recommender produces structurally reasonable meal plans across BMI, age, and dietary-pattern profiles.

The current project is evaluated as a standalone software system, not as a thesis or academic study. The matrix is a product-quality and guidance-alignment check.

Run:

```bash
python -m ai_nutritionist.evaluation
```

Latest local run:

| Profile | Pattern | Age | BMI | Category | Goal | Target kcal | Calorie delta | Avg. quality | Baseline proxy | Lift | Protein | Produce | Sodium | Sat. fat |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| young_underweight | omnivore | 24 | 17.9 | Underweight | support gradual weight gain | 2714 | 9.8% | 99.5 | 81.4 | 18.1 | yes | yes | no | yes |
| adult_normal | omnivore | 30 | 23.1 | Normal | maintain balanced intake | 2682 | 8.5% | 99.3 | 82.0 | 17.3 | yes | yes | no | yes |
| adult_normal_vegan | vegan | 32 | 23.0 | Normal | maintain balanced intake | 2223 | 5.9% | 99.1 | 83.1 | 16.0 | yes | yes | no | yes |
| adult_normal_mediterranean | mediterranean | 30 | 23.1 | Normal | maintain balanced intake | 2682 | 8.5% | 99.3 | 82.0 | 17.3 | yes | yes | no | yes |
| adult_normal_vegetarian | vegetarian | 38 | 23.2 | Normal | maintain balanced intake | 2056 | 3.1% | 98.8 | 83.2 | 15.6 | yes | yes | yes | yes |
| adult_normal_keto_style | keto_style | 30 | 23.1 | Normal | maintain balanced intake | 2682 | 20.2% | 99.5 | 75.5 | 24.0 | yes | yes | no | yes |
| midlife_overweight | omnivore | 45 | 27.2 | Overweight | support gradual weight reduction | 2435 | 3.0% | 99.5 | 84.4 | 15.1 | yes | yes | yes | yes |
| midlife_obese | omnivore | 45 | 33.3 | Severely overweight | support gradual weight reduction | 2363 | 3.0% | 99.4 | 84.4 | 15.0 | yes | yes | no | yes |
| older_normal | omnivore | 72 | 24.2 | Normal | maintain balanced intake | 1924 | 10.9% | 98.8 | 80.9 | 17.9 | yes | yes | yes | yes |

Summary:

- Profiles evaluated: 9
- Average internal quality score: 99.2
- Average constraint-only baseline proxy score: 81.9
- Average quality lift versus baseline proxy: 17.4
- Average calorie-target delta: 8.1%
- Profiles with protein each meal: 9/9
- Profiles with produce each meal: 9/9
- Profiles within sodium guardrails: 3/9
- Profiles within saturated-fat guardrails: 9/9

## Interpretation

The matrix is a product-quality smoke check for structurally reasonable outputs: each profile receives meals with protein, produce, high-fiber choices, calorie-target tracking, and guardrail checks. It is not clinical validation and does not prove health outcomes. The baseline proxy is a transparent constraint-only scoring comparison, not a separate clinical model. Some Mediterranean-style and keto-style profiles exceed strict per-meal sodium allocation; this is documented rather than hidden. Keto-style keeps carbohydrate and saturated-fat guardrails tighter, but can sit farther below the broad daily calorie estimate because the mode is intentionally low-carbohydrate. The quality score is an internal guardrail metric for tests and evaluation, not a customer-facing claim of clinical accuracy, nutrition adequacy, safety, or medical effectiveness.
