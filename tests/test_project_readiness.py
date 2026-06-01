from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_project_has_packaging_metadata_and_console_entrypoint():
    pyproject = ROOT / "pyproject.toml"
    assert pyproject.exists()

    metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = metadata["project"]

    assert project["name"] == "ai-nutritionist"
    assert project["requires-python"] == ">=3.11"
    assert "ai-nutritionist" in project["scripts"]
    assert project["scripts"]["ai-nutritionist"] == "ai_nutritionist.cli:main"


def test_repo_has_ci_docker_and_deploy_readiness_files():
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    dockerfile = ROOT / "Dockerfile"
    dockerignore = ROOT / ".dockerignore"

    assert workflow.exists()
    assert dockerfile.exists()
    assert dockerignore.exists()

    workflow_text = workflow.read_text(encoding="utf-8")
    assert "python-version: [\"3.11\", \"3.12\"]" in workflow_text
    assert "pytest -q" in workflow_text
    assert "python -m ai_nutritionist.evaluation" in workflow_text
    assert "--weekly" in workflow_text
    assert "forbidden artifact" in workflow_text

    docker_text = dockerfile.read_text(encoding="utf-8")
    assert "streamlit run app.py" in docker_text
    assert "EXPOSE 8501" in docker_text


def test_model_and_data_cards_exist_and_are_linked_from_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    model_card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
    data_card = (ROOT / "DATA_CARD.md").read_text(encoding="utf-8")

    assert "[MODEL_CARD.md](MODEL_CARD.md)" in readme
    assert "[DATA_CARD.md](DATA_CARD.md)" in readme
    assert "weak labels" in model_card.lower()
    assert "not clinical" in model_card.lower()
    assert "USDA FoodData Central" in data_card
    assert "curated Mediterranean" in data_card


def test_streamlit_entrypoint_is_thin_and_ui_modules_exist():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "from ai_nutritionist.ui.app import run_app" in app_source
    assert len(app_source.splitlines()) <= 5

    expected_modules = [
        "ai_nutritionist/ui/app.py",
        "ai_nutritionist/ui/components.py",
        "ai_nutritionist/ui/config.py",
        "ai_nutritionist/ui/state.py",
        "ai_nutritionist/ui/tabs.py",
    ]
    for module in expected_modules:
        assert (ROOT / module).exists()
