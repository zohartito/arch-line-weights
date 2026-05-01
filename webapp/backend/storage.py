"""Storage abstraction — local filesystem stub, S3-compatible swap-in later.

The interface is deliberately tiny: ``write_upload``, ``output_path``,
``read_output``, ``exists``. When we move to Tigris/R2, only this module
changes; nothing else in the backend imports a filesystem path.

Files live under ``<storage_root>/<job_id>/``:

    <job_id>/input.ai     — original upload
    <job_id>/output.ai    — pipeline output (after compute)
    <job_id>/meta.json    — small bookkeeping blob (future: replace with DB row)
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass
class JobPaths:
    """Resolved on-disk layout for a single job."""

    root: Path
    input_path: Path
    output_path: Path
    meta_path: Path


class LocalStorage:
    """Filesystem-backed storage. Each job gets its own directory.

    The class is intentionally synchronous — even at the SaaS scale this
    project targets (10 s compute, 30 MB files), the filesystem and zstd
    work overlaps poorly with asyncio anyway. Callers run it via
    ``starlette.concurrency.run_in_threadpool`` if they need async.
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def paths_for(self, job_id: str) -> JobPaths:
        """Return the conventional layout for a job, creating the dir as needed."""
        root = self._root / job_id
        root.mkdir(parents=True, exist_ok=True)
        return JobPaths(
            root=root,
            input_path=root / "input.ai",
            output_path=root / "output.ai",
            meta_path=root / "meta.json",
        )

    def write_upload(self, job_id: str, source: BinaryIO, *, filename: str) -> JobPaths:
        """Stream ``source`` to ``<job_id>/input.ai``.

        ``filename`` is preserved (we copy it into ``input<ext>`` plus an
        adjacent ``original_name.txt``) so the pipeline output can be named
        nicely on download. We don't trust ``filename`` for path construction
        — just for display.
        """
        paths = self.paths_for(job_id)
        # Honour the original extension so pikepdf opens the file.
        suffix = Path(filename).suffix.lower() or ".ai"
        if suffix not in (".ai", ".pdf"):
            suffix = ".ai"
        paths = JobPaths(
            root=paths.root,
            input_path=paths.root / f"input{suffix}",
            output_path=paths.root / f"output{suffix}",
            meta_path=paths.meta_path,
        )
        with paths.input_path.open("wb") as f:
            shutil.copyfileobj(source, f, length=1024 * 1024)
        (paths.root / "original_name.txt").write_text(filename, encoding="utf-8")
        return paths

    def exists(self, job_id: str) -> bool:
        return (self._root / job_id).is_dir()

    def output_size(self, job_id: str) -> int | None:
        paths = self.paths_for(job_id)
        if paths.output_path.exists():
            return paths.output_path.stat().st_size
        return None

    def read_output_bytes(self, job_id: str) -> bytes:
        """Used by tests / small downloads. Real downloads stream via FileResponse."""
        return self.paths_for(job_id).output_path.read_bytes()

    def original_name(self, job_id: str) -> str | None:
        f = self._root / job_id / "original_name.txt"
        if f.exists():
            return f.read_text(encoding="utf-8")
        return None

    def cleanup_job(self, job_id: str) -> None:
        """Wipe a job's directory. Used by retention sweeps + tests."""
        target = self._root / job_id
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
