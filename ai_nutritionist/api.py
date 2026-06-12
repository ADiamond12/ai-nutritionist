from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Literal
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, StringConstraints
import uvicorn

from ai_nutritionist.constants import SAFETY_DISCLAIMER, SYSTEM_NAME
from ai_nutritionist.feedback import FeedbackEntry, FeedbackStore
from ai_nutritionist.presentation import public_daily_payload, public_weekly_payload
from ai_nutritionist.recommender import recommend, recommend_week


PreferenceTerm = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class RecommendationRequest(BaseModel):
    weight_kg: float = Field(ge=30, le=220)
    height_cm: float = Field(ge=120, le=230)
    age: int = Field(ge=10, le=100)
    sex: Literal["female", "male", "unspecified"] = "unspecified"
    activity: Literal["sedentary", "light", "moderate", "active"] = "moderate"
    dietary_pattern: Literal["mediterranean", "omnivore", "vegetarian", "vegan", "keto_style"] = "mediterranean"
    body_fat_pct: float | None = Field(default=None, ge=5, le=60)
    weight_goal: Literal["auto", "maintain", "lose", "gain"] = "auto"
    goal_focus: Literal["balanced", "higher_protein", "higher_fiber", "lighter_meals", "lower_sodium"] = "balanced"
    avoid_terms: list[PreferenceTerm] = Field(default_factory=list, max_length=20)
    preferred_terms: list[PreferenceTerm] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=4, ge=3, le=5)
    planner_mode: Literal["legacy", "hybrid_v2"] = "hybrid_v2"


class WeeklyRecommendationRequest(RecommendationRequest):
    days: int = Field(default=7, ge=1, le=14)


class FeedbackRequest(BaseModel):
    scope: Literal["plan", "meal"]
    label: str = Field(min_length=1, max_length=80)
    sentiment: Literal["liked", "not_liked"]
    dietary_pattern: str = Field(min_length=1, max_length=40)
    weight_goal: str = Field(min_length=1, max_length=40)
    avoid_terms: list[PreferenceTerm] = Field(default_factory=list, max_length=10)


def create_app(feedback_db_path: Path | str | None = None) -> FastAPI:
    app = FastAPI(
        title=SYSTEM_NAME,
        summary="Profile-aware wellness meal planner API",
        version="0.5.0",
    )
    resolved_feedback_db_path = (
        Path(feedback_db_path) if feedback_db_path is not None else _default_feedback_db_path()
    ).resolve()
    feedback_readback_enabled = _env_flag("AI_NUTRITIONIST_ENABLE_FEEDBACK_READBACK")
    store: FeedbackStore | None = None
    store_lock = Lock()

    def feedback_store() -> FeedbackStore:
        nonlocal store
        if store is None:
            with store_lock:
                if store is None:
                    store = FeedbackStore(resolved_feedback_db_path)
        return store

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "system_name": SYSTEM_NAME, "safety_notice": SAFETY_DISCLAIMER}

    @app.post("/recommend/daily", response_model=dict[str, Any])
    def recommend_daily(request: RecommendationRequest) -> dict[str, Any]:
        result = recommend(**request.model_dump())
        return public_daily_payload(result)

    @app.post("/recommend/weekly", response_model=dict[str, Any])
    def recommend_weekly(request: WeeklyRecommendationRequest) -> dict[str, Any]:
        data = request.model_dump()
        days = int(data.pop("days"))
        result = recommend_week(**data, days=days)
        return public_weekly_payload(result)

    @app.post("/feedback", status_code=201)
    def create_feedback(request: FeedbackRequest) -> dict[str, Any]:
        count = feedback_store().add(FeedbackEntry(**request.model_dump()))
        return {"stored": True, "count": count}

    @app.get("/feedback")
    def list_feedback() -> dict[str, Any]:
        if not feedback_readback_enabled:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Feedback readback is disabled by default. Set "
                    "AI_NUTRITIONIST_ENABLE_FEEDBACK_READBACK=1 only for local review."
                ),
            )
        entries = feedback_store().list_entries()
        return {"count": len(entries), "entries": [entry.__dict__ for entry in entries]}

    return app


def _default_feedback_db_path() -> Path:
    configured = os.environ.get("AI_NUTRITIONIST_FEEDBACK_DB")
    if configured:
        return Path(configured)
    return Path(".local") / "feedback.sqlite"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


app = create_app()


def main() -> int:
    uvicorn.run("ai_nutritionist.api:app", host="127.0.0.1", port=8000, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
