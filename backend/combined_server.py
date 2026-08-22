from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
API_STARTUP_TIMEOUT_SECONDS = 45
PROCESS_GROUP_OPTIONS = (
    {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    if os.name == "nt"
    else {"start_new_session": True}
)


def _port(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer port.") from exc
    if not 1 <= value <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535.")
    return value


def _npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _run_setup() -> None:
    public_data_mode = os.getenv("PUBLIC_DATA_MODE", "sqlite").strip().lower()
    if public_data_mode == "parquet":
        subprocess.run(
            [sys.executable, "-m", "app.public_data_lake", "bootstrap"],
            cwd=BACKEND_DIR,
            check=True,
        )
    elif public_data_mode == "sqlite":
        subprocess.run(
            [sys.executable, "-m", "app.database_snapshot"],
            cwd=BACKEND_DIR,
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            check=True,
        )
    else:
        raise ValueError("PUBLIC_DATA_MODE must be either 'sqlite' or 'parquet'.")

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "billing_alembic.ini", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )


def _wait_for_api(process: subprocess.Popen[bytes], api_port: int) -> None:
    endpoint = f"http://127.0.0.1:{api_port}/api/health"
    deadline = time.monotonic() + API_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(f"FastAPI exited during startup with code {exit_code}.")
        try:
            with urlopen(endpoint, timeout=2) as response:  # noqa: S310 - fixed loopback URL
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.25)
    raise TimeoutError("FastAPI did not become healthy before the startup deadline.")


def _stop(processes: list[subprocess.Popen[bytes]]) -> None:
    running = [process for process in processes if process.poll() is None]
    if os.name == "nt":
        for process in running:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return
    for process in running:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 10
    while running and time.monotonic() < deadline:
        running = [process for process in running if process.poll() is None]
        if running:
            time.sleep(0.1)
    for process in running:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main() -> int:
    public_port = _port("PORT", 10000)
    api_port = _port("INTERNAL_API_PORT", 8000)
    if public_port == api_port:
        raise ValueError("PORT and INTERNAL_API_PORT must be different.")
    if not (FRONTEND_DIR / "package.json").is_file():
        raise FileNotFoundError(f"Frontend package not found at {FRONTEND_DIR}.")

    processes: list[subprocess.Popen[bytes]] = []
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True
        _stop(processes)

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        _run_setup()
        api_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            cwd=BACKEND_DIR,
            **PROCESS_GROUP_OPTIONS,
        )
        processes.append(api_process)
        _wait_for_api(api_process, api_port)

        frontend_environment = os.environ.copy()
        frontend_environment["BACKEND_URL"] = f"http://127.0.0.1:{api_port}"
        frontend_process = subprocess.Popen(
            [
                _npm_executable(),
                "run",
                "start",
                "--",
                "--hostname",
                "0.0.0.0",
                "--port",
                str(public_port),
            ],
            cwd=FRONTEND_DIR,
            env=frontend_environment,
            **PROCESS_GROUP_OPTIONS,
        )
        processes.append(frontend_process)

        while not stopping:
            for label, process in (("FastAPI", api_process), ("Next.js", frontend_process)):
                exit_code = process.poll()
                if exit_code is not None:
                    print(f"{label} exited unexpectedly with code {exit_code}.", flush=True)
                    return exit_code or 1
            time.sleep(0.5)
        return 0
    finally:
        _stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
