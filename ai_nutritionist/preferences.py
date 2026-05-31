from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd


GOAL_FOCUS_OPTIONS = {
    "balanced",
    "higher_protein",
    "higher_fiber",
    "lighter_meals",
    "lower_sodium",
}


@dataclass(frozen=True)
class RecommendationPreferences:
    goal_focus: str = "balanced"
    avoid_terms: list[str] | None = None
    preferred_terms: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["avoid_terms"] = self.avoid_terms or []
        data["preferred_terms"] = self.preferred_terms or []
        return data


def build_preferences(
    *,
    goal_focus: str = "balanced",
    avoid_terms: str | Iterable[str] | None = None,
    preferred_terms: str | Iterable[str] | None = None,
) -> RecommendationPreferences:
    focus = goal_focus.strip().lower().replace(" ", "_") if goal_focus else "balanced"
    if focus not in GOAL_FOCUS_OPTIONS:
        allowed = ", ".join(sorted(GOAL_FOCUS_OPTIONS))
        raise ValueError(f"goal_focus must be one of: {allowed}")
    return RecommendationPreferences(
        goal_focus=focus,
        avoid_terms=_parse_terms(avoid_terms),
        preferred_terms=_parse_terms(preferred_terms),
    )


def apply_preferences(
    foods: pd.DataFrame,
    preferences: RecommendationPreferences,
    *,
    meal_name: str,
) -> pd.DataFrame:
    if foods.empty:
        return foods.copy()

    adjusted = foods.copy()
    avoid_terms = preferences.avoid_terms or []
    if avoid_terms:
        avoid_mask = adjusted["food_name"].map(lambda value: _matches_any(value, avoid_terms))
        adjusted = adjusted.loc[~avoid_mask].copy()
    if adjusted.empty:
        return adjusted

    adjusted["preference_match"] = adjusted["food_name"].map(
        lambda value: float(_matches_any(value, preferences.preferred_terms or []))
    )
    adjusted["score"] = adjusted.get("score", 0).astype(float)
    adjusted["score"] += adjusted["preference_match"] * 35
    adjusted["score"] += _focus_adjustment(adjusted, preferences.goal_focus, meal_name)
    return adjusted.sort_values(["score", "protein_g", "fiber_g"], ascending=[False, False, False]).reset_index(drop=True)


def _parse_terms(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_terms = value.replace(";", ",").replace("\n", ",").split(",")
    else:
        raw_terms = list(value)
    terms = []
    for term in raw_terms:
        cleaned = str(term).strip().lower()
        if cleaned and cleaned not in terms:
            terms.append(cleaned)
    return terms


def _matches_any(value: object, terms: list[str]) -> bool:
    text = str(value).lower()
    return any(term in text for term in terms)


def _focus_adjustment(foods: pd.DataFrame, focus: str, meal_name: str) -> pd.Series:
    calories = pd.to_numeric(foods["calories"], errors="coerce").fillna(0).clip(lower=1)
    protein_density = pd.to_numeric(foods["protein_g"], errors="coerce").fillna(0) / calories
    fiber_density = pd.to_numeric(foods["fiber_g"], errors="coerce").fillna(0) / calories
    sodium_density = pd.to_numeric(foods["sodium_mg"], errors="coerce").fillna(0) / calories
    saturated_density = pd.to_numeric(foods["saturated_fat_g"], errors="coerce").fillna(0) / calories

    if focus == "higher_protein":
        return _bounded(protein_density, 0.02, 0.18) * 18
    if focus == "higher_fiber":
        return _bounded(fiber_density, 0.0, 0.08) * 18
    if focus == "lighter_meals":
        return (1 - _bounded(calories, 80, 360)) * 18
    if focus == "lower_sodium":
        return (1 - _bounded(sodium_density, 0.0, 3.0)) * 22 + (1 - _bounded(saturated_density, 0.0, 0.04)) * 5
    return pd.Series(0.0, index=foods.index)


def _bounded(series: pd.Series, low: float, high: float) -> pd.Series:
    if high <= low:
        return series * 0
    return ((series - low) / (high - low)).clip(0, 1)
