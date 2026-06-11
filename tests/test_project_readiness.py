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
    assert project["scripts"]["ai-nutritionist-api"] == "ai_nutritionist.api:main"
    assert any(dependency.startswith("fastapi>=0.115") for dependency in project["dependencies"])


def test_repo_has_ci_docker_and_deploy_readiness_files():
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    dockerfile = ROOT / "Dockerfile"
    dockerignore = ROOT / ".dockerignore"

    assert workflow.exists()
    assert dockerfile.exists()
    assert dockerignore.exists()

    workflow_text = workflow.read_text(encoding="utf-8")
    assert "python-version: [\"3.11\", \"3.12\"]" in workflow_text
    assert "ruff check" in workflow_text
    assert "mypy ai_nutritionist" in workflow_text
    assert "pytest -q" in workflow_text
    assert "python -m ai_nutritionist.evaluation" in workflow_text
    assert "--weekly" in workflow_text
    assert "docker build -t ai-nutritionist:ci ." in workflow_text
    assert "docker run --rm -d --name ai-nutritionist-ci -p 8501:8501 ai-nutritionist:ci" in workflow_text
    assert "http://127.0.0.1:8501/_stcore/health" in workflow_text
    assert "docker logs ai-nutritionist-ci" in workflow_text
    assert "docker stop ai-nutritionist-ci" in workflow_text
    assert "forbidden artifact" in workflow_text

    docker_text = dockerfile.read_text(encoding="utf-8")
    assert "streamlit run app.py" in docker_text
    assert "EXPOSE 8501" in docker_text
    assert "HEALTHCHECK" in docker_text
    assert "_stcore/health" in docker_text
    assert "--no-cache-dir" in docker_text
    assert "pip install -e ." not in docker_text


def test_repo_has_security_and_deployment_automation_files():
    dependabot = ROOT / ".github" / "dependabot.yml"
    codeql = ROOT / ".github" / "workflows" / "codeql.yml"
    streamlit_config = ROOT / ".streamlit" / "config.toml"
    hf_space = ROOT / "docs" / "deployment" / "huggingface-space-README.md"
    streamlit_cloud = ROOT / "docs" / "deployment" / "STREAMLIT_COMMUNITY_CLOUD.md"

    assert dependabot.exists()
    assert codeql.exists()
    assert streamlit_config.exists()
    assert hf_space.exists()
    assert streamlit_cloud.exists()

    assert "package-ecosystem: \"pip\"" in dependabot.read_text(encoding="utf-8")
    assert "github/codeql-action/analyze" in codeql.read_text(encoding="utf-8")
    hf_space_text = hf_space.read_text(encoding="utf-8")
    assert "sdk: docker" in hf_space_text
    assert "app_port: 8501" in hf_space_text
    assert "data/recipes" in hf_space_text
    assert ".env" in hf_space_text
    assert "local feedback databases" in hf_space_text
    assert "hosting platform" in hf_space_text

    streamlit_cloud_text = streamlit_cloud.read_text(encoding="utf-8")
    assert "data/foods_catalog.csv" in streamlit_cloud_text
    assert "data/mediterranean_foods.csv" in streamlit_cloud_text
    assert "data/recipes" in streamlit_cloud_text
    assert "hosting platform" in streamlit_cloud_text


def test_runtime_requirements_exclude_dev_only_dependencies():
    requirements = {
        line.split(">=", maxsplit=1)[0].split("==", maxsplit=1)[0].strip().lower()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = "\n".join(pyproject["project"]["optional-dependencies"]["dev"]).lower()

    assert "pytest" not in requirements
    assert "httpx" not in requirements
    assert "pytest" in dev_dependencies
    assert "httpx" in dev_dependencies


def test_neural_ranker_cache_is_bounded_for_deployment_memory():
    from ai_nutritionist.ranker import get_neural_ranker

    assert get_neural_ranker.cache_info().maxsize == 1


def test_model_and_data_cards_exist_and_are_linked_from_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    model_card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
    data_card = (ROOT / "DATA_CARD.md").read_text(encoding="utf-8")
    guideline_alignment = (ROOT / "docs" / "GUIDELINE_ALIGNMENT.md").read_text(encoding="utf-8")

    assert "[MODEL_CARD.md](MODEL_CARD.md)" in readme
    assert "[DATA_CARD.md](DATA_CARD.md)" in readme
    assert "[docs/GUIDELINE_ALIGNMENT.md](docs/GUIDELINE_ALIGNMENT.md)" in readme
    assert "weak labels" in model_card.lower()
    assert "not clinical" in model_card.lower()
    assert "USDA FoodData Central" in data_card
    assert "curated Mediterranean" in data_card
    assert "not a clinical nutrition system" in guideline_alignment
    assert "WHO healthy diet" in guideline_alignment


def test_streamlit_entrypoint_is_thin_and_ui_modules_exist():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    ui_source = (ROOT / "ai_nutritionist" / "ui" / "app.py").read_text(encoding="utf-8")

    assert "from ai_nutritionist.ui.app import run_app" in app_source
    assert len(app_source.splitlines()) <= 5
    assert "chicken, walnuts" in ui_source
    assert "beans, berries, oats" in ui_source
    assert "fish, chicken, nuts" not in ui_source
    assert "salmon, beans, berries" not in ui_source

    expected_modules = [
        "ai_nutritionist/ui/app.py",
        "ai_nutritionist/ui/components.py",
        "ai_nutritionist/ui/config.py",
        "ai_nutritionist/ui/state.py",
        "ai_nutritionist/ui/tabs.py",
    ]
    for module in expected_modules:
        assert (ROOT / module).exists()


def test_public_screenshot_artifacts_and_refresh_guidance_are_current():
    screenshot_dir = ROOT / "docs" / "screenshots"
    screenshot_readme = (screenshot_dir / "README.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    expected_screenshots = [
        "streamlit-meal-plan.png",
        "streamlit-weekly-plan.png",
        "streamlit-daily-nutrition.png",
        "streamlit-alternatives.png",
        "streamlit-mobile-day-detail.png",
    ]
    for filename in expected_screenshots:
        path = screenshot_dir / filename
        assert path.exists()
        assert path.stat().st_size > 10_000
        assert filename in screenshot_readme
        assert filename in readme

    for path in screenshot_dir.glob("*.png"):
        assert path.name in screenshot_readme

    assert "default 75 kg, 180 cm, age 30" in screenshot_readme
    assert "chicken, walnuts" in screenshot_readme
    assert "beans, berries, oats" in screenshot_readme
    assert "avoid `fish" not in screenshot_readme.lower()
    assert "prefer `salmon" not in screenshot_readme.lower()
    assert "Plan Fit" in screenshot_readme
    assert "Ranker:" in screenshot_readme
    assert "quality_score" in screenshot_readme
    assert "neural_score" in screenshot_readme
