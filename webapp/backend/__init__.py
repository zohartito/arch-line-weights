"""arch-line-weights webapp backend.

FastAPI app that wraps the existing pure-Python pipeline (apply_saas +
poche_saas) behind a small REST API. This is a Phase D scaffold — local
filesystem storage, in-memory job table, no auth, no payments. The
production stack (Fly.io + Tigris + Neon + Redis+RQ) plugs in by
swapping `storage.py` and the `compute.run_job` runner.
"""

from __future__ import annotations

__version__ = "0.0.1"
