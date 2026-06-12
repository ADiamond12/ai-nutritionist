from __future__ import annotations

from pathlib import Path
import os
import socket
import subprocess
import sys
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env.pop("AI_NUTRITIONIST_ENABLE_API_FEEDBACK", None)
    env.pop("AI_NUTRITIONIST_ENABLE_FEEDBACK_READBACK", None)
    local_feedback_path = ROOT / ".local" / "feedback.sqlite"
    feedback_db_existed_before = local_feedback_path.exists()

    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_health(port, process)
        _fetch(f"http://127.0.0.1:{port}/", timeout=5)
        if not feedback_db_existed_before and local_feedback_path.exists():
            raise RuntimeError(f"Streamlit first-screen smoke created unexpected feedback DB: {local_feedback_path}")
    finally:
        _stop(process)
    print(f"Streamlit smoke ok on 127.0.0.1:{port}")
    return 0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(port: int, process: subprocess.Popen[str]) -> None:
    url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + 60
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            raise RuntimeError(f"Streamlit exited early with {process.returncode}\n{output}")
        try:
            body = _fetch(url, timeout=3)
            if body.strip().lower() == "ok":
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(1)
    raise TimeoutError(f"Streamlit health endpoint did not become ready: {last_error}")


def _fetch(url: str, *, timeout: int) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")


def _stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
