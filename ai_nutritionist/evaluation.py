from dataclasses import asdict, dataclass
import json

from ai_nutritionist.recommender import recommend


@dataclass(frozen=True)
class EvaluationRow:
    label: str
    dietary_pattern: str
    age: int
    bmi: float
    bmi_category: str
    profile_goal: str
    calorie_target: int
    average_quality_score: float
    protein_each_meal: bool
    produce_each_meal: bool
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
        result = recommend(activity="moderate", dietary_pattern=dietary_pattern, **profile_args)
        rows.append(_row_from_result(label, dietary_pattern, result))

    average_quality = round(
        sum(row.average_quality_score for row in rows) / len(rows),
        1,
    )
    summary = {
        "profiles_evaluated": len(rows),
        "average_quality_score": average_quality,
        "profiles_with_protein_each_meal": sum(row.protein_each_meal for row in rows),
        "profiles_with_produce_each_meal": sum(row.produce_each_meal for row in rows),
        "profiles_with_sodium_guardrails": sum(row.sodium_within_guardrails for row in rows),
        "profiles_with_saturated_fat_guardrails": sum(row.saturated_fat_within_guardrails for row in rows),
    }
    return EvaluationReport(rows=rows, summary=summary)


def _row_from_result(label: str, dietary_pattern: str, result) -> EvaluationRow:
    return EvaluationRow(
        label=label,
        dietary_pattern=dietary_pattern,
        age=result.age,
        bmi=result.bmi.value,
        bmi_category=result.bmi.category_label,
        profile_goal=result.profile_goal,
        calorie_target=result.daily_targets.calories,
        average_quality_score=round(sum(meal.quality_score for meal in result.meals) / len(result.meals), 1),
        protein_each_meal=all(meal.guidance_checks["has_protein"] for meal in result.meals),
        produce_each_meal=all(meal.guidance_checks["has_produce"] for meal in result.meals),
        sodium_within_guardrails=all(meal.guidance_checks["sodium_within_meal_limit"] for meal in result.meals),
        saturated_fat_within_guardrails=all(
            meal.guidance_checks["saturated_fat_within_meal_limit"] for meal in result.meals
        ),
    )


def main() -> int:
    print(json.dumps(evaluate_profiles().to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
