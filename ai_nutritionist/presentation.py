from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ai_nutritionist.plan_outputs import build_grocery_list
from ai_nutritionist.recommender import MealRecommendation, RecommendationResult, WeeklyRecommendationResult


INTERNAL_ITEM_KEYS = {"score", "neural_score", "heuristic_score", "model_name", "quality_score"}


def public_daily_payload(result: RecommendationResult) -> dict[str, Any]:
    return {
        "system_name": result.system_name,
        "safety_notice": result.safety_notice,
        "health_summary": result.health_summary,
        "bmi": asdict(result.bmi),
        "age": result.age,
        "sex": result.sex,
        "activity": result.activity,
        "weight_goal": result.weight_goal,
        "profile_goal": result.profile_goal,
        "daily_targets": asdict(result.daily_targets),
        "daily_totals": result.daily_totals,
        "daily_progress": result.daily_progress,
        "macro_percentages": result.macro_percentages,
        "preferences": result.preferences,
        "meals": [_public_meal(meal) for meal in result.meals],
        "grocery_list": build_grocery_list(result),
    }


def public_weekly_payload(result: WeeklyRecommendationResult) -> dict[str, Any]:
    return {
        "system_name": result.system_name,
        "safety_notice": result.safety_notice,
        "dietary_pattern": result.dietary_pattern,
        "weight_goal": result.weight_goal,
        "nutrition_focus": result.nutrition_focus,
        "weekly_totals": result.weekly_totals,
        "weekly_averages": result.weekly_averages,
        "variety_counts": result.variety_counts,
        "days": [
            {
                "day_name": day.day_name,
                "rotation_focus": day.rotation_focus,
                "plan": public_daily_payload(day.result),
            }
            for day in result.days
        ],
        "grocery_list": build_grocery_list(result),
    }


def _public_meal(meal: MealRecommendation) -> dict[str, Any]:
    return {
        "name": meal.name,
        "title": meal.title,
        "items": [_public_item(item) for item in meal.items],
        "totals": meal.totals,
        "guidance_checks": meal.guidance_checks,
        "explanations": meal.explanations,
        "alternatives": {
            group: [_public_item(item) for item in alternatives]
            for group, alternatives in meal.alternatives.items()
        },
    }


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in INTERNAL_ITEM_KEYS}
