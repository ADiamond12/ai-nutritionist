from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import warnings

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ai_nutritionist.constants import MEAL_NAMES
from ai_nutritionist.data import load_food_catalog
from ai_nutritionist.profile import NutritionProfile, build_profile
from ai_nutritionist.scoring import meal_target, score_foods


NUMERIC_FEATURES = [
    "serving_grams",
    "calories",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sugars_g",
    "sodium_mg",
    "saturated_fat_g",
    "protein_density",
    "fiber_density",
    "sodium_density",
    "saturated_fat_density",
    "sugar_density",
    "meal_calorie_target",
    "meal_protein_target",
    "meal_fiber_target",
    "bmi_category_id",
    "age",
    "vegetarian_flag",
    "vegan_flag",
    "minimally_processed_flag",
]

CATEGORICAL_FEATURES = ["food_group", "meal_name", "profile_goal"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

MODEL_NAME = "Neural MLP food ranker"
ALGORITHM_NAME = "MLPRegressor neural food ranker"

MEDITERRANEAN_TERMS = (
    "greek",
    "souvlaki",
    "fasolada",
    "horta",
    "horiatiki",
    "dakos",
    "lentil soup",
    "chickpea",
    "gigantes",
    "sardines",
    "salmon",
    "cod plaki",
    "olive oil",
)

LOW_PRACTICALITY_STANDALONE_TERMS = (
    "alfalfa sprouts",
    "pumpkin seeds",
    "flax seeds",
    "chia seeds",
    "sesame seeds",
    "sunflower seeds",
    "fruit dressing",
    "dressing",
)

TRAINING_PROFILES = [
    {"weight_kg": 58, "height_cm": 180, "age": 24, "sex": "male", "activity": "moderate"},
    {"weight_kg": 75, "height_cm": 180, "age": 30, "sex": "male", "activity": "moderate"},
    {"weight_kg": 88, "height_cm": 180, "age": 45, "sex": "male", "activity": "moderate"},
    {"weight_kg": 108, "height_cm": 180, "age": 45, "sex": "male", "activity": "moderate"},
    {"weight_kg": 70, "height_cm": 170, "age": 72, "sex": "female", "activity": "light"},
]


@dataclass(frozen=True)
class NeuralRanker:
    pipeline: Pipeline
    training_rows: int
    algorithm: str = ALGORITHM_NAME
    target: str = "weak-supervised USDA nutrition quality and profile-fit score"


def rank_foods_with_neural_model(
    foods: pd.DataFrame,
    profile: NutritionProfile,
    meal_name: str,
    *,
    data_dir: str | None = None,
) -> pd.DataFrame:
    if foods.empty:
        result = foods.copy()
        result["neural_score"] = []
        result["score"] = []
        result.attrs["ranker_algorithm"] = ALGORITHM_NAME
        return result

    ranker = get_neural_ranker(data_dir)
    feature_frame = _feature_frame(foods, profile, meal_name)
    neural_scores = ranker.pipeline.predict(feature_frame[FEATURE_COLUMNS])

    heuristic = score_foods(foods, profile, meal_name)
    heuristic_scores = heuristic.set_index("fdc_id")["score"] if "fdc_id" in heuristic else pd.Series(dtype=float)

    ranked = foods.copy()
    ranked["neural_score"] = pd.Series(neural_scores, index=ranked.index).clip(0, 100).round(3)
    if "fdc_id" in ranked.columns and not heuristic_scores.empty:
        ranked["heuristic_score"] = ranked["fdc_id"].map(heuristic_scores).fillna(ranked["neural_score"])
    else:
        ranked["heuristic_score"] = ranked["neural_score"]
    ranked["score"] = ((ranked["neural_score"] * 0.55) + (ranked["heuristic_score"] * 0.45)).round(3)
    if "minimally_processed" in ranked.columns:
        ranked.loc[~ranked["minimally_processed"].astype(bool), "score"] -= 5
    ranked.loc[ranked["source"].str.contains("Curated Mediterranean", case=False, na=False), "score"] += 16
    ranked.loc[ranked["food_name"].map(_is_mediterranean_food), "score"] += 8
    ranked.loc[ranked["food_name"].map(_is_low_practicality_standalone), "score"] -= 28
    ranked.attrs["ranker_algorithm"] = ranker.algorithm
    ranked.attrs["training_rows"] = ranker.training_rows
    return ranked.sort_values(["score", "protein_g", "fiber_g"], ascending=[False, False, False]).reset_index(drop=True)


@lru_cache(maxsize=4)
def get_neural_ranker(data_dir: str | None = None) -> NeuralRanker:
    catalog = load_food_catalog(data_dir)
    training_foods = catalog
    if len(training_foods) > 1200:
        training_foods = training_foods.sample(n=1200, random_state=42).reset_index(drop=True)

    frames = []
    labels = []
    for profile_args in TRAINING_PROFILES:
        profile = build_profile(
            weight_kg=float(str(profile_args["weight_kg"])),
            height_cm=float(str(profile_args["height_cm"])),
            age=int(float(str(profile_args["age"]))),
            sex=str(profile_args["sex"]),
            activity=str(profile_args["activity"]),
        )
        for meal_name in MEAL_NAMES:
            heuristic = score_foods(training_foods, profile, meal_name)
            frames.append(_feature_frame(heuristic, profile, meal_name))
            labels.extend(heuristic["score"].tolist())

    train_x = pd.concat(frames, ignore_index=True)[FEATURE_COLUMNS]
    train_y = pd.Series(labels).clip(0, 100)

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )
    model = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        alpha=0.0008,
        learning_rate_init=0.003,
        max_iter=220,
        random_state=42,
        early_stopping=True,
        n_iter_no_change=18,
        validation_fraction=0.15,
    )
    pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(train_x, train_y)
    return NeuralRanker(pipeline=pipeline, training_rows=len(train_x))


def _feature_frame(foods: pd.DataFrame, profile: NutritionProfile, meal_name: str) -> pd.DataFrame:
    frame = foods.copy()
    target = meal_target(profile, meal_name)
    calories = pd.to_numeric(frame["calories"], errors="coerce").fillna(0).clip(lower=1)

    frame["protein_density"] = pd.to_numeric(frame["protein_g"], errors="coerce").fillna(0) / calories
    frame["fiber_density"] = pd.to_numeric(frame["fiber_g"], errors="coerce").fillna(0) / calories
    frame["sodium_density"] = pd.to_numeric(frame["sodium_mg"], errors="coerce").fillna(0) / calories
    frame["saturated_fat_density"] = pd.to_numeric(frame["saturated_fat_g"], errors="coerce").fillna(0) / calories
    frame["sugar_density"] = pd.to_numeric(frame["sugars_g"], errors="coerce").fillna(0) / calories
    frame["meal_calorie_target"] = target.calories
    frame["meal_protein_target"] = target.protein_g
    frame["meal_fiber_target"] = target.fiber_g
    frame["bmi_category_id"] = profile.bmi.category_id
    frame["age"] = profile.age
    frame["meal_name"] = meal_name
    frame["profile_goal"] = profile.profile_goal
    frame["vegetarian_flag"] = frame.get("vegetarian", False).astype(float)
    frame["vegan_flag"] = frame.get("vegan", False).astype(float)
    frame["minimally_processed_flag"] = frame.get("minimally_processed", False).astype(float)

    for column in NUMERIC_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].fillna("").astype(str)
    return frame[FEATURE_COLUMNS]


def _is_mediterranean_food(food_name: object) -> bool:
    text = str(food_name).lower()
    return any(term in text for term in MEDITERRANEAN_TERMS)


def _is_low_practicality_standalone(food_name: object) -> bool:
    text = str(food_name).lower()
    return any(term in text for term in LOW_PRACTICALITY_STANDALONE_TERMS)
