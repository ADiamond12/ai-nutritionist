from pathlib import Path

from fastapi.testclient import TestClient

from ai_nutritionist.api import create_app


def test_api_health_and_openapi_are_available():
    client = TestClient(create_app())

    health = client.get("/health")
    openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "not medical advice" in health.json()["safety_notice"].lower()
    assert openapi.status_code == 200
    assert "/recommend/daily" in openapi.json()["paths"]


def test_api_daily_and_weekly_recommendations_hide_internal_scores():
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
