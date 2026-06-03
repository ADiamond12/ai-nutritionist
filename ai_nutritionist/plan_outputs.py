from __future__ import annotations

from io import StringIO
from typing import Any
import csv

from ai_nutritionist.recommender import RecommendationResult, WeeklyRecommendationResult


def build_grocery_list(result: RecommendationResult | WeeklyRecommendationResult) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in _iter_food_items(result):
        key = (str(item.get("food_group", "")), str(item.get("food_name", "")))
        if key not in grouped:
            grouped[key] = {
                "food_group": key[0],
                "food_name": key[1],
                "serving_grams": 0.0,
                "times_used": 0,
                "calories": 0.0,
                "protein_g": 0.0,
                "fiber_g": 0.0,
            }
        grouped[key]["serving_grams"] += float(item.get("serving_grams", 0) or 0)
        grouped[key]["times_used"] += 1
        grouped[key]["calories"] += float(item.get("calories", 0) or 0)
        grouped[key]["protein_g"] += float(item.get("protein_g", 0) or 0)
        grouped[key]["fiber_g"] += float(item.get("fiber_g", 0) or 0)

    rows = []
    for row in grouped.values():
        rows.append(
            {
                **row,
                "serving_grams": round(row["serving_grams"], 1),
                "calories": round(row["calories"], 1),
                "protein_g": round(row["protein_g"], 1),
                "fiber_g": round(row["fiber_g"], 1),
            }
        )
    return sorted(rows, key=lambda item: (item["food_group"], item["food_name"]))


def grocery_list_csv(grocery_list: list[dict[str, Any]]) -> str:
    output = StringIO()
    fieldnames = ["food_group", "food_name", "serving_grams", "times_used", "calories", "protein_g", "fiber_g"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in grocery_list:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return output.getvalue()


def _iter_food_items(result: RecommendationResult | WeeklyRecommendationResult):
    if isinstance(result, WeeklyRecommendationResult):
        for day in result.days:
            for meal in day.result.meals:
                yield from meal.items
        return
    for meal in result.meals:
        yield from meal.items
