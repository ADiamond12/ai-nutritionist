from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time

from fastapi.testclient import TestClient

import ai_nutritionist.api as api_module
from ai_nutritionist.api import create_app
from ai_nutritionist.feedback import FeedbackEntry, FeedbackStore


def test_api_health_and_openapi_are_available():
    client = TestClient(create_app())

    health = client.get("/health")
    openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "not medical advice" in health.json()["safety_notice"].lower()
    assert openapi.status_code == 200
    assert "/recommend/daily" in openapi.json()["paths"]


def test_api_health_and_openapi_do_not_create_default_feedback_store(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    health = client.get("/health")
    openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert openapi.status_code == 200
    assert not (tmp_path / ".local").exists()


def test_api_daily_and_weekly_recommendations_hide_internal_scores(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    request = {
        "weight_kg": 75,
        "height_cm": 180,
        "age": 30,
        "sex": "male",
        "dietary_pattern": "mediterranean",
        "weight_goal": "lose",
        "top_k": 3,
    }

    daily = client.post("/recommend/daily", json=request)
    weekly = client.post("/recommend/weekly", json={**request, "days": 7})

    assert daily.status_code == 200, daily.text
    assert weekly.status_code == 200, weekly.text
    assert daily.json()["grocery_list"]
    assert len(weekly.json()["days"]) == 7
    combined = f"{daily.text}\n{weekly.text}"
    assert "quality_score" not in combined
    assert "neural_score" not in combined
    assert "model_name" not in combined
    assert not (tmp_path / ".local").exists()


def test_api_default_feedback_store_is_created_only_when_feedback_is_used(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())

    response = client.post(
        "/feedback",
        json={
            "scope": "meal",
            "label": "Lunch",
            "sentiment": "not_liked",
            "dietary_pattern": "mediterranean",
            "weight_goal": "lose",
            "avoid_terms": ["tuna", "beans"],
        },
    )

    assert response.status_code == 201, response.text
    assert (tmp_path / ".local" / "feedback.sqlite").exists()


def test_api_feedback_db_env_path_is_resolved_when_app_is_created(tmp_path: Path, monkeypatch):
    initial_path = tmp_path / "initial" / "feedback.sqlite"
    later_path = tmp_path / "later" / "feedback.sqlite"
    monkeypatch.setenv("AI_NUTRITIONIST_FEEDBACK_DB", str(initial_path))
    client = TestClient(create_app())
    monkeypatch.setenv("AI_NUTRITIONIST_FEEDBACK_DB", str(later_path))

    response = client.post(
        "/feedback",
        json={
            "scope": "meal",
            "label": "Lunch",
            "sentiment": "liked",
            "dietary_pattern": "mediterranean",
            "weight_goal": "maintain",
            "avoid_terms": [],
        },
    )

    assert response.status_code == 201, response.text
    assert initial_path.exists()
    assert not later_path.exists()


def test_api_default_feedback_db_path_is_anchored_when_app_is_created(tmp_path: Path, monkeypatch):
    initial_cwd = tmp_path / "initial"
    later_cwd = tmp_path / "later"
    initial_cwd.mkdir()
    later_cwd.mkdir()
    monkeypatch.chdir(initial_cwd)
    client = TestClient(create_app())
    monkeypatch.chdir(later_cwd)

    response = client.post(
        "/feedback",
        json={
            "scope": "meal",
            "label": "Lunch",
            "sentiment": "liked",
            "dietary_pattern": "mediterranean",
            "weight_goal": "maintain",
            "avoid_terms": [],
        },
    )

    assert response.status_code == 201, response.text
    assert (initial_cwd / ".local" / "feedback.sqlite").exists()
    assert not (later_cwd / ".local").exists()


def test_api_feedback_store_is_initialized_once_for_concurrent_feedback_requests(tmp_path: Path, monkeypatch):
    created_paths: list[Path] = []

    class SlowFeedbackStore:
        def __init__(self, path: Path | str):
            created_paths.append(Path(path))
            time.sleep(0.02)
            self.store = FeedbackStore(path)

        def add(self, entry: FeedbackEntry) -> int:
            return self.store.add(entry)

        def list_entries(self) -> list[FeedbackEntry]:
            return self.store.list_entries()

    monkeypatch.setattr(api_module, "FeedbackStore", SlowFeedbackStore)
    client = TestClient(create_app(feedback_db_path=tmp_path / "feedback.sqlite"))

    def submit_feedback(index: int):
        return client.post(
            "/feedback",
            json={
                "scope": "meal",
                "label": f"Meal {index}",
                "sentiment": "liked",
                "dietary_pattern": "mediterranean",
                "weight_goal": "maintain",
                "avoid_terms": [],
            },
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(submit_feedback, range(5)))

    assert all(response.status_code == 201 for response in responses)
    assert len(created_paths) == 1
    assert client.get("/feedback").json()["count"] == 5


def test_api_feedback_endpoint_persists_to_local_sqlite(tmp_path: Path):
    db_path = tmp_path / "feedback.sqlite"
    client = TestClient(create_app(feedback_db_path=db_path))

    response = client.post(
        "/feedback",
        json={
            "scope": "meal",
            "label": "Lunch",
            "sentiment": "not_liked",
            "dietary_pattern": "mediterranean",
            "weight_goal": "lose",
            "avoid_terms": ["tuna", "beans"],
        },
    )
    log = client.get("/feedback")

    assert response.status_code == 201, response.text
    assert response.json()["stored"] is True
    assert response.json()["count"] == 1
    assert log.status_code == 200
    assert log.json()["entries"][0]["avoid_terms"] == ["tuna", "beans"]
