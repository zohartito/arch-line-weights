from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

from backend import dev_console
from backend.config import local_vite_cors_origins


def test_find_available_port_skips_occupied_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        occupied = sock.getsockname()[1]

        available = dev_console.find_available_port("127.0.0.1", occupied, limit=20)

    assert available != occupied
    assert available >= occupied


def test_find_available_port_skips_excluded_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        excluded = sock.getsockname()[1]

    available = dev_console.find_available_port("127.0.0.1", excluded, exclude={excluded})

    assert available != excluded
    assert available > excluded


def test_choose_server_ports_keeps_backend_and_frontend_distinct(monkeypatch) -> None:
    calls: list[tuple[int, set[int]]] = []

    def fake_find_available_port(
        _host: str,
        preferred: int,
        *,
        limit: int = dev_console.PORT_SEARCH_LIMIT,
        exclude: set[int] | None = None,
    ) -> int:
        del limit
        excluded = set(exclude or set())
        calls.append((preferred, excluded))
        if preferred == 8766:
            return 8766
        assert 8766 in excluded
        return 8767

    monkeypatch.setattr(dev_console, "find_available_port", fake_find_available_port)

    backend_port, frontend_port = dev_console.choose_server_ports(
        "127.0.0.1",
        backend_preferred=8766,
        frontend_preferred=8765,
    )

    assert backend_port == 8766
    assert frontend_port == 8767
    assert calls == [(8766, set()), (8765, {8766})]


def test_build_backend_env_sets_pythonpath_and_cors(tmp_path: Path) -> None:
    root = tmp_path / "webapp"
    root.mkdir()
    env = dev_console.build_backend_env(root, {"PYTHONPATH": "existing"})

    pythonpath = env["PYTHONPATH"].split(os.pathsep)
    assert pythonpath[:2] == [str(root), str(root.parent / "src")]
    assert "existing" in pythonpath
    assert env["ARCHLW_CORS_ORIGINS"] == ",".join(local_vite_cors_origins())


def test_build_backend_env_adds_exact_frontend_origin(tmp_path: Path) -> None:
    root = tmp_path / "webapp"
    root.mkdir()
    env = dev_console.build_backend_env(
        root,
        {"ARCHLW_CORS_ORIGINS": "http://localhost:5173"},
        frontend_origin="http://127.0.0.1:5192",
    )

    assert env["ARCHLW_CORS_ORIGINS"] == "http://localhost:5173,http://127.0.0.1:5192"


def test_commands_use_known_ports_and_strict_frontend_port() -> None:
    assert dev_console.backend_command(host="127.0.0.1", port=8012, reload=False) == [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8012",
    ]
    assert dev_console.backend_command(host="127.0.0.1", port=8012, reload=True)[-1] == "--reload"
    assert dev_console.frontend_command(npm="npm", host="127.0.0.1", port=5174) == [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        "5174",
        "--strictPort",
    ]


def test_parse_args_supports_no_open_for_automated_smoke() -> None:
    args = dev_console.parse_args(["--backend-port", "8010", "--frontend-port", "5174", "--no-open"])

    assert args.backend_port == 8010
    assert args.frontend_port == 5174
    assert args.no_open is True
