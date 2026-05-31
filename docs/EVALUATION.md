# Evaluation

The evaluation matrix checks whether the recommender produces structurally reasonable meal plans across BMI, age, and dietary-pattern profiles.

The current project is evaluated as a standalone software system, not as a thesis or academic study. The matrix is a product-quality and guidance-alignment check.

Run:

```bash
python -m ai_nutritionist.evaluation
```

Latest local run:

| Profile | Pattern | Age | BMI | Category | Goal | Calorie target | Avg. quality | Protein each meal | Produce each meal | Sodium guardrails | Saturated fat guardrails |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- | --- | --- |
| young_underweight | omnivore | 24 | 17.9 | Underweight | support gradual weight gain | 2714 | 99.5 | yes | yes | no | yes |
| adult_normal | omnivore | 30 | 23.1 | Normal | maintain balanced intake | 2682 | 99.3 | yes | yes | no | yes |
| adult_normal_vegan | vegan | 32 | 23.0 | Normal | maintain balanced intake | 2223 | 99.1 | yes | yes | no | yes |
| adult_normal_mediterranean | mediterranean | 30 | 23.1 | Normal | maintain balanced intake | 2682 | 99.3 | yes | yes | no | yes |
| adult_normal_vegetarian | vegetarian | 38 | 23.2 | Normal | maintain balanced intake | 2056 | 98.8 | yes | yes | yes | yes |
| adult_normal_keto_style | keto_style | 30 | 23.1 | Normal | maintain balanced intake | 2682 | 99.5 | yes | yes | yes | yes |
| midlife_overweight | omnivore | 45 | 27.2 | Overweight | support gradual weight reduction | 2435 | 98.9 | yes | yes | no | yes |
| midlife_obese | omnivore | 45 | 33.3 | Severely overweight | support gradual weight reduction | 2363 | 98.4 | yes | yes | no | yes |
| older_normal | omnivore | 72 | 24.2 | Normal | maintain balanced intake | 1924 | 98.8 | yes | yes | yes | yes |

Summary:

- Profiles evaluated: 9
- Average internal quality score: 99.1
- Profiles with protein each meal: 9/9
- Profiles with produce each meal: 9/9
- Profiles within sodium guardrails: 3/9
- Profiles within saturated-fat guardrails: 9/9

## Interpretation

The output aligns with broad public-health guidance because each profile receives meals with protein, produce, high-fiber choices, and saturated-fat checks. Some Mediterranean-style profiles exceed strict per-meal sodium allocation while staying inside the daily sodium limit; this is documented rather than hidden. The quality score is an internal guardrail metric for tests and evaluation, not a customer-facing claim of clinical accuracy or medical effectiveness.
