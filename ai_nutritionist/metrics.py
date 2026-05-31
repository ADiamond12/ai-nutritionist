from dataclasses import dataclass
from typing import Iterable, Mapping

import pandas as pd


@dataclass(frozen=True)
class BMIResult:
    value: float
    category_id: int
    category_label: str


BMI_CATEGORY_LABELS = {
    0: "Severely underweight",
    1: "Underweight",
    2: "Normal",
    3: "Overweight",
    4: "Severely overweight",
}

MACRO_COLUMNS = ["Calories", "Fats", "Proteins", "Carbohydrates", "Fibre", "Sugars"]


def bmi_category_id(bmi: float) -> int:
    if bmi <= 16:
        return 0
    if bmi <= 18.5:
        return 1
    if bmi <= 25:
        return 2
    if bmi <= 30:
        return 3
    return 4


def calculate_bmi(weight_kg: float, height_cm: float) -> BMIResult:
    if weight_kg <= 0:
        raise ValueError("weight_kg must be greater than zero")
    if height_cm <= 0:
        raise ValueError("height_cm must be greater than zero")

    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
    category_id = bmi_category_id(bmi)
    return BMIResult(
        value=bmi,
        category_id=category_id,
        category_label=BMI_CATEGORY_LABELS[category_id],
    )


def age_category_id(age: int) -> int:
    if age <= 20:
        return 0
    if age <= 40:
        return 1
    if age <= 60:
        return 2
    if age <= 80:
        return 3
    return 4


def macro_totals(items: Iterable[Mapping[str, object]]) -> dict[str, float]:
    totals = {column: 0.0 for column in MACRO_COLUMNS}
    for item in items:
        for column in MACRO_COLUMNS:
            totals[column] += float(item.get(column, 0) or 0)
    return totals


def filter_foods_by_veg(foods: pd.DataFrame, veg_filter: int) -> pd.DataFrame:
    if veg_filter not in {-1, 0, 1}:
        raise ValueError("veg_filter must be -1, 0, or 1")
    if veg_filter == -1:
        return foods.reset_index(drop=True)

    flag = str(veg_filter)
    normalized = foods["VegNovVeg"].fillna("").astype(str).str.strip()
    return foods.loc[normalized == flag].reset_index(drop=True)
