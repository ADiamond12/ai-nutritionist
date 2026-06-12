# Hybrid Recommender V2

Hybrid Recommender V2 evolves AI Nutritionist from ranked food selection plus greedy assembly into a deterministic two-stage planning system.

## Planning Stages

1. The local MLP ranker, preference signals, dietary filters, and meal blueprints generate a structured candidate plan.
2. Hybrid V2 evaluates the complete day and searches bounded same-group substitutions and portion adjustments.
3. A candidate change is accepted only when it improves the complete-day objective and preserves already-passing hard limits.
4. The final plan is rebuilt with updated totals, guidance checks, titles, explanations, alternatives, and public-safe planner notes.

The legacy planner remains available through `planner_mode="legacy"` and `--planner-mode legacy` so evaluation can compare identical inputs and targets.

## Multi-Objective Behavior

The internal objective balances:

- daily and meal-level calorie-target fit;
- protein and fiber shortfalls;
- sodium, saturated-fat, and sugar excess;
- keto-style carbohydrate limits;
- protein, produce, and food-group structure;
- duplicate food IDs and food families;
- selected goal focus, including lower sodium, higher protein, and higher fiber.

Search is deterministic. It uses a fixed candidate order, portion-factor grid, iteration budget, and tie behavior. No external API, randomness, or hidden hosted model is required.

## Hard-Limit Preservation

During each accepted optimization step, Hybrid V2 preserves daily and meal-level limits that are already passing:

- sodium;
- saturated fat;
- fruit-aware meal sugar checks;
- keto-style carbohydrate limits.

An existing failed limit can still improve. This prevents the optimizer from sacrificing an already-passing guardrail solely to improve calorie fit.

## Public Diagnostics

Streamlit, CLI, and API outputs may show:

- planner mode;
- substitution count;
- portion-adjustment count;
- short remaining-constraint notes.

Daily and weekly plans both expose public-safe planner summaries. Weekly summaries aggregate the per-day Hybrid V2 substitutions, portion adjustments, and remaining notes.

Internal ranking scores and optimization-objective values are not exposed publicly.

## Paired Benchmark

The current 9-profile paired benchmark reports:

| Metric | Legacy | Hybrid V2 |
| --- | ---: | ---: |
| Average calorie-target delta | 7.8% | 1.7% |
| Meal-level sodium pass rate | 92.6% | 100.0% |
| Daily sodium pass rate | 100.0% | 100.0% |
| Structural feasibility rate | 100.0% | 100.0% |

See [EVALUATION.md](EVALUATION.md) for definitions and interpretation.

## Current Boundary

The current catalog mixes atomic foods, meal components, opaque prepared dishes, and a small reviewed recipe-backed pilot in one flat runtime schema. Hybrid V2 therefore optimizes practical plate compositions; it does not claim broad ingredient-level recipe decomposition beyond the reviewed pilot or clinical diet optimization.
