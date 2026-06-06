from dataclasses import asdict, dataclass
import json

from ai_nutritionist.recommender import MealRecommendation, RecommendationResult, recommend


@dataclass(frozen=True)
class EvaluationRow:
    label: str
    dietary_pattern: str
    age: int
    bmi: float
    bmi_category: str
    profile_goal: str
    calorie_target: int
    calorie_delta_pct: float
    protein_coverage_pct: float
    fiber_coverage_pct: float
    protein_each_meal: bool
    produce_each_meal: bool
    structure_feasible: bool
    daily_sodium_within_guardrail: bool
    meal_sodium_pass_count: int
    sodium_within_guardrails: bool
    saturated_fat_within_guardrails: bool


@dataclass(frozen=True)
class EvaluationReport:
    rows: list[EvaluationRow]
    summary: dict[str, float | int]

    def to_dict(self) -> dict[str, object]:
        return {"rows": [asdict(row) for row in self.rows], "summary": self.summary}


DEFAULT_PROFILES = [
    {"label": "young_underweight", "weight_kg": 58, "height_cm": 180, "age": 24, "sex": "male"},
    {"label": "adult_normal", "weight_kg": 75, "height_cm": 180, "age": 30, "sex": "male"},
    {
        "label": "adult_normal_vegan",
        "weight_kg": 68,
        "height_cm": 172,
        "age": 32,
        "sex": "female",
        "dietary_pattern": "vegan",
    },
    {
        "label": "adult_normal_mediterranean",
        "weight_kg": 75,
        "height_cm": 180,
        "age": 30,
        "sex": "male",
        "dietary_pattern": "mediterranean",
    },
    {
        "label": "adult_normal_vegetarian",
        "weight_kg": 64,
        "height_cm": 166,
        "age": 38,
        "sex": "female",
        "dietary_pattern": "vegetarian",
    },
    {
        "label": "adult_normal_keto_style",
        "weight_kg": 75,
        "height_cm": 180,
        "age": 30,
        "sex": "male",
        "dietary_pattern": "keto_style",
        "body_fat_pct": 18,
        "goal_focus": "higher_protein",
    },
    {"label": "midlife_overweight", "weight_kg": 88, "height_cm": 180, "age": 45, "sex": "male"},
    {"label": "midlife_obese", "weight_kg": 108, "height_cm": 180, "age": 45, "sex": "male"},
    {"label": "older_normal", "weight_kg": 70, "height_cm": 170, "age": 72, "sex": "female"},
]


def evaluate_profiles(profiles: list[dict[str, object]] | None = None) -> EvaluationReport:
    rows = []
    for profile in profiles or DEFAULT_PROFILES:
        profile_args = dict(profile)
        label = str(profile_args.pop("label"))
        dietary_pattern = str(profile_args.pop("dietary_pattern", "omnivore"))
        result = recommend(
            weight_kg=float(str(profile_args.pop("weight_kg"))),
            height_cm=float(str(profile_args.pop("height_cm"))),
            age=int(float(str(profile_args.pop("age")))),
            sex=str(profile_args.pop("sex", "unspecified")),
            activity=str(profile_args.pop("activity", "moderate")),
            dietary_pattern=dietary_pattern,
            body_fat_pct=_optional_float(profile_args.pop("body_fat_pct", None)),
            weight_goal=str(profile_args.pop("weight_goal", "auto")),
            goal_focus=str(profile_args.pop("goal_focus", "balanced")),
        )
        rows.append(_row_from_result(label, dietary_pattern, result))

    summary = {
        "profiles_evaluated": len(rows),
        "average_calorie_delta_pct": round(
            sum(row.calorie_delta_pct for row in rows) / len(rows),
            1,
        ),
        "average_protein_coverage_pct": round(sum(row.protein_coverage_pct for row in rows) / len(rows), 1),
        "average_fiber_coverage_pct": round(sum(row.fiber_coverage_pct for row in rows) / len(rows), 1),
        "profiles_with_protein_each_meal": sum(row.protein_each_meal for row in rows),
        "profiles_with_produce_each_meal": sum(row.produce_each_meal for row in rows),
        "profiles_with_structure_feasible": sum(row.structure_feasible for row in rows),
        "profiles_with_daily_sodium_guardrail": sum(row.daily_sodium_within_guardrail for row in rows),
        "meal_sodium_pass_rate_pct": round(
            (sum(row.meal_sodium_pass_count for row in rows) / (len(rows) * 3)) * 100,
            1,
        ),
        "profiles_with_sodium_guardrails": sum(row.sodium_within_guardrails for row in rows),
        "profiles_with_saturated_fat_guardrails": sum(row.saturated_fat_within_guardrails for row in rows),
    }
    return EvaluationReport(rows=rows, summary=summary)


def compare_planners(profiles: list[dict[str, object]] | None = None) -> dict[str, float | int]:
    comparison_profiles = profiles or DEFAULT_PROFILES
    legacy_results = [_recommend_profile(profile, "legacy") for profile in comparison_profiles]
    hybrid_results = [_recommend_profile(profile, "hybrid_v2") for profile in comparison_profiles]
    legacy_meals = [meal for result in legacy_results for meal in result.meals]
    hybrid_meals = [meal for result in hybrid_results for meal in result.meals]
    return {
        "profiles_evaluated": len(comparison_profiles),
        "legacy_average_calorie_delta_pct": _average_calorie_delta(legacy_results),
        "hybrid_average_calorie_delta_pct": _average_calorie_delta(hybrid_results),
        "legacy_meal_sodium_pass_rate_pct": _meal_check_pass_rate(legacy_meals, "sodium_within_meal_limit"),
        "hybrid_meal_sodium_pass_rate_pct": _meal_check_pass_rate(hybrid_meals, "sodium_within_meal_limit"),
        "legacy_daily_sodium_pass_rate_pct": _daily_limit_pass_rate(
            legacy_results, "sodium_mg", "sodium_mg_limit"
        ),
        "hybrid_daily_sodium_pass_rate_pct": _daily_limit_pass_rate(
            hybrid_results, "sodium_mg", "sodium_mg_limit"
        ),
        "legacy_structure_feasibility_rate_pct": _structure_feasibility_rate(legacy_results),
        "hybrid_structure_feasibility_rate_pct": _structure_feasibility_rate(hybrid_results),
        "profiles_changed_by_hybrid_v2": sum(
            legacy.to_dict() != hybrid.to_dict()
            for legacy, hybrid in zip(legacy_results, hybrid_results)
        ),
    }


def _recommend_profile(profile: dict[str, object], planner_mode: str) -> RecommendationResult:
    profile_args = dict(profile)
    profile_args.pop("label")
    return recommend(
        weight_kg=float(str(profile_args.pop("weight_kg"))),
        height_cm=float(str(profile_args.pop("height_cm"))),
        age=int(float(str(profile_args.pop("age")))),
        sex=str(profile_args.pop("sex", "unspecified")),
        activity=str(profile_args.pop("activity", "moderate")),
        dietary_pattern=str(profile_args.pop("dietary_pattern", "omnivore")),
        body_fat_pct=_optional_float(profile_args.pop("body_fat_pct", None)),
        weight_goal=str(profile_args.pop("weight_goal", "auto")),
        goal_focus=str(profile_args.pop("goal_focus", "balanced")),
        planner_mode=planner_mode,
    )


def _average_calorie_delta(results: list[RecommendationResult]) -> float:
    return round(sum(_calorie_delta_pct(result) for result in results) / len(results), 1)


def _meal_check_pass_rate(meals: list[MealRecommendation], check: str) -> float:
    return round((sum(meal.guidance_checks[check] for meal in meals) / len(meals)) * 100, 1)


def _daily_limit_pass_rate(results: list[RecommendationResult], total_key: str, limit_key: str) -> float:
    passing = sum(
        float(result.daily_totals[total_key]) <= float(getattr(result.daily_targets, limit_key))
        for result in results
    )
    return round((passing / len(results)) * 100, 1)


def _structure_feasibility_rate(results: list[RecommendationResult]) -> float:
    feasible = sum(
        all(
            meal.guidance_checks["has_protein"]
            and meal.guidance_checks["has_produce"]
            and meal.guidance_checks["diverse_food_groups"]
            for meal in result.meals
        )
        for result in results
    )
    return round((feasible / len(results)) * 100, 1)


def _row_from_result(label: str, dietary_pattern: str, result) -> EvaluationRow:
    calorie_delta_pct = _calorie_delta_pct(result)
    meal_sodium_pass_count = sum(meal.guidance_checks["sodium_within_meal_limit"] for meal in result.meals)
    return EvaluationRow(
        label=label,
        dietary_pattern=dietary_pattern,
        age=result.age,
        bmi=result.bmi.value,
        bmi_category=result.bmi.category_label,
        profile_goal=result.profile_goal,
        calorie_target=result.daily_targets.calories,
        calorie_delta_pct=calorie_delta_pct,
        protein_coverage_pct=_coverage(result.daily_totals["protein_g"], result.daily_targets.protein_g),
        fiber_coverage_pct=_coverage(result.daily_totals["fiber_g"], result.daily_targets.fiber_g),
        protein_each_meal=all(meal.guidance_checks["has_protein"] for meal in result.meals),
        produce_each_meal=all(meal.guidance_checks["has_produce"] for meal in result.meals),
        structure_feasible=all(
            meal.guidance_checks["has_protein"]
            and meal.guidance_checks["has_produce"]
            and meal.guidance_checks["diverse_food_groups"]
            for meal in result.meals
        ),
        daily_sodium_within_guardrail=result.daily_totals["sodium_mg"] <= result.daily_targets.sodium_mg_limit,
        meal_sodium_pass_count=meal_sodium_pass_count,
        sodium_within_guardrails=all(meal.guidance_checks["sodium_within_meal_limit"] for meal in result.meals),
        saturated_fat_within_guardrails=all(
            meal.guidance_checks["saturated_fat_within_meal_limit"] for meal in result.meals
        ),
    )


def _calorie_delta_pct(result) -> float:
    target = max(float(result.daily_targets.calories), 1.0)
    delta = abs(float(result.daily_totals["calories"]) - target)
    return round((delta / target) * 100, 1)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(str(value))


def _coverage(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return round(min(100.0, (value / target) * 100), 1)


def main() -> int:
    print(json.dumps({"evaluation": evaluate_profiles().to_dict(), "planner_comparison": compare_planners()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
