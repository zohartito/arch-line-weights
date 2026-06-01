"""One-command local launcher for the webapp designer console."""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Mapping, Sequence

from .config import local_vite_cors_origins


DEFAULT_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 5173
PORT_SEARCH_LIMIT = 20


def webapp_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_available_port(
    host: str,
    preferred: int,
    *,
    limit: int = PORT_SEARCH_LIMIT,
    exclude: set[int] | None = None,
) -> int:
    """Return the first bindable port at or after ``preferred``."""
    excluded = set(exclude or set())
    for port in range(preferred, preferred + limit):
        if port in excluded:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"no available port found from {preferred} through {preferred + limit - 1}")


def choose_server_ports(
    host: str,
    *,
    backend_preferred: int,
    frontend_preferred: int,
) -> tuple[int, int]:
    backend_port = find_available_port(host, backend_preferred)
    frontend_port = find_available_port(host, frontend_preferred, exclude={backend_port})
    return backend_port, frontend_port


def build_pythonpath(root: Path, env: Mapping[str, str]) -> str:
    entries = [str(root), str(root.parent / "src")]
    existing = env.get("PYTHONPATH")
    if existing:
        entries.extend(existing.split(os.pathsep))
    return os.pathsep.join(dict.fromkeys(entry for entry in entries if entry))


def build_backend_env(
    root: Path,
    base_env: Mapping[str, str],
    *,
    frontend_origin: str | None = None,
) -> dict[str, str]:
    env = dict(base_env)
    env["PYTHONPATH"] = build_pythonpath(root, env)
    origins = _parse_origins(env.get("ARCHLW_CORS_ORIGINS")) or local_vite_cors_origins()
    if frontend_origin and frontend_origin not in origins:
        origins.append(frontend_origin)
    env["ARCHLW_CORS_ORIGINS"] = ",".join(origins)
    return env


def build_frontend_env(base_env: Mapping[str, str], *, backend_url: str) -> dict[str, str]:
    env = dict(base_env)
    env["VITE_API_BASE_URL"] = backend_url
    return env


def _parse_origins(value: str | None) -> list[str]:
    if not value:
        return []
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def backend_command(*, host: str, port: int, reload: bool) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        command.append("--reload")
    return command


def frontend_command(*, npm: str, host: str, port: int) -> list[str]:
    return [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        host,
        "--port",
        str(port),
        "--strictPort",
    ]


def wait_for_http(url: str, *, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    return False


def terminate_processes(processes: Sequence[subprocess.Popen[object]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local arch-line-weights designer console.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Local interface for both dev servers.")
    parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)
    parser.add_argument("--npm", default="npm", help="npm executable to use for the SvelteKit dev server.")
    parser.add_argument("--storage-root", help="Optional ARCHLW_STORAGE_ROOT for local runs.")
    parser.add_argument("--reload", action="store_true", help="Run the backend with uvicorn --reload.")
    parser.add_argument("--no-open", action="store_true", help="Print the URL without opening a browser.")
    return parser.parse_args(argv)


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = webapp_root()
    frontend_root = root / "frontend"
    if not (frontend_root / "package.json").is_file():
        print(f"frontend package.json not found at {frontend_root}", file=sys.stderr)
        return 2
    if not (frontend_root / "node_modules").is_dir():
        print(
            "frontend dependencies are missing; run `npm install` in webapp/frontend once, then retry.",
            file=sys.stderr,
        )
        return 2

    try:
        backend_port, frontend_port = choose_server_ports(
            args.host,
            backend_preferred=args.backend_port,
            frontend_preferred=args.frontend_port,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    backend_url = f"http://{args.host}:{backend_port}"
    frontend_url = f"http://{args.host}:{frontend_port}/"
    backend_env = build_backend_env(root, os.environ, frontend_origin=frontend_url.rstrip("/"))
    if args.storage_root:
        backend_env["ARCHLW_STORAGE_ROOT"] = args.storage_root
    frontend_env = build_frontend_env(os.environ, backend_url=backend_url)

    processes: list[subprocess.Popen[object]] = []
    try:
        backend = subprocess.Popen(
            backend_command(host=args.host, port=backend_port, reload=args.reload),
            cwd=root,
            env=backend_env,
        )
        processes.append(backend)
        if not wait_for_http(f"{backend_url}/api/health", timeout=30):
            print("backend did not become ready in time", file=sys.stderr)
            return 1

        frontend = subprocess.Popen(
            frontend_command(npm=args.npm, host=args.host, port=frontend_port),
            cwd=frontend_root,
            env=frontend_env,
        )
        processes.append(frontend)
        if not wait_for_http(frontend_url, timeout=30):
            print("frontend did not become ready in time", file=sys.stderr)
            return 1

        print(f"Designer console ready: {frontend_url}")
        print(f"Backend API: {backend_url}")
        print("Press Ctrl+C to stop both servers.")
        if not args.no_open:
            webbrowser.open(frontend_url)

        while True:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    return int(return_code)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping designer console.")
        return 0
    finally:
        terminate_processes(processes)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
