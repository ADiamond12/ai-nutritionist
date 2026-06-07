import os
import subprocess
import sys
from pathlib import Path


def test_cli_smoke_runs_from_another_working_directory_with_ascii_output(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()

    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "cli.py"),
            "--weight",
            "75",
            "--height",
            "180",
            "--age",
            "24",
            "--veg",
            "-1",
            "--topk",
            "2",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    completed.stdout.encode("ascii")
    assert "AI Nutritionist recommendation system" in completed.stdout
    assert "not medical advice" in completed.stdout.lower()
    assert "Totals ->" in completed.stdout
    assert "Planner: hybrid_v2" in completed.stdout


def test_cli_accepts_focus_and_preference_flags(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "cli.py"),
            "--weight",
            "75",
            "--height",
            "180",
            "--age",
            "30",
            "--goal-focus",
            "lower_sodium",
            "--avoid",
            "fish,chicken",
            "--prefer",
            "beans",
            "--top-k",
            "3",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    completed.stdout.encode("ascii")
    assert "Focus: lower_sodium" in completed.stdout
    assert "Avoiding: fish, chicken" in completed.stdout


def test_cli_accepts_keto_and_body_fat_flags(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "cli.py"),
            "--weight",
            "75",
            "--height",
            "180",
            "--age",
            "30",
            "--dietary-pattern",
            "keto_style",
            "--body-fat",
            "18",
            "--topk",
            "3",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    completed.stdout.encode("ascii")
    assert "Diet: keto_style" in completed.stdout
    assert "Body fat: 18.0%" in completed.stdout
    assert "Macro split ->" in completed.stdout


def test_cli_accepts_weight_goal_and_weekly_plan_flags(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "cli.py"),
            "--weight",
            "125",
            "--height",
            "200",
            "--age",
            "30",
            "--sex",
            "male",
            "--dietary-pattern",
            "mediterranean",
            "--weight-goal",
            "lose",
            "--weekly",
            "--topk",
            "3",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    completed.stdout.encode("ascii")
    assert "Weight goal: lose" in completed.stdout
    assert "Planner: hybrid_v2" in completed.stdout
    assert "Weekly Mediterranean rotation" in completed.stdout
    assert "Monday" in completed.stdout
    assert "Sunday" in completed.stdout


def test_cli_hides_internal_plan_fit_scores_from_user_output(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "cli.py"),
            "--weight",
            "75",
            "--height",
            "180",
            "--age",
            "30",
            "--top-k",
            "3",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    completed.stdout.encode("ascii")
    assert "PlanFit" not in completed.stdout
    assert "Plan Fit" not in completed.stdout
    assert "Neural:" not in completed.stdout
    assert "Neural MLP" not in completed.stdout
    assert "Ranker:" not in completed.stdout
