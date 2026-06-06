# Evaluation

The evaluation suite checks whether the recommender produces structurally feasible plans across BMI, age, goal, and dietary-pattern profiles. It also runs identical profiles through the legacy planner and the default Hybrid V2 planner for a paired engineering comparison.

Run:

```bash
python -m ai_nutritionist.evaluation
```

## Latest Local Result

The current 9-profile matrix covers underweight, normal, overweight, severely overweight, older-adult, Mediterranean, vegetarian, vegan, and keto-style profiles.

| Metric | Legacy | Hybrid V2 |
| --- | ---: | ---: |
| Average calorie-target delta | 8.1% | 2.7% |
| Meal-level sodium pass rate | 74.1% | 96.3% |
| Daily sodium pass rate | 100.0% | 100.0% |
| Structural feasibility rate | 100.0% | 100.0% |
| Profiles changed by Hybrid V2 | n/a | 9/9 |

Hybrid V2 also preserves already-passing daily and meal-level sodium, saturated-fat, sugar, and keto-style carbohydrate limits while evaluating candidate changes.

## Metric Definitions

- **Calorie-target delta:** absolute difference between generated daily calories and the app's estimated target.
- **Meal-level sodium pass rate:** percentage of meals within the app's allocated meal sodium guardrail.
- **Daily sodium pass rate:** percentage of profiles within the app's daily sodium guardrail.
- **Structural feasibility:** every meal contains protein, produce, and at least three food groups.
- **Protein/fiber coverage:** generated daily total divided by the app target, capped at 100% for aggregate reporting.

The legacy and Hybrid V2 runs use identical inputs and targets. The comparison does not use internal quality scores or the optimizer objective as public evidence.

## Interpretation

This is a deterministic product-quality and guidance-alignment benchmark. The measured result shows that Hybrid V2 improves target fit and meal-level sodium allocation on the current profile matrix without reducing structural feasibility or daily sodium compliance.

The benchmark does not establish nutrient adequacy, clinical safety, health outcomes, medical effectiveness, or guaranteed weight change. Keto-style mode can remain farther below the broad daily calorie estimate because it preserves its tighter low-carbohydrate and saturated-fat constraints.
