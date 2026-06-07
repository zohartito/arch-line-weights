"""Public-safe local Illustrator visual review summaries."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

VALID_VISUAL_CHECK_STATUSES = ("needs_review", "accepted", "rejected", "blocked")

_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:file://)?(?:/Users/|/private/|/var/folders/|/tmp/|/Volumes/|[A-Z]:\\|\\\\)"
)
_LOCAL_PATH_WITH_EXT_RE = re.compile(
    r"(?i)(?:file://)?(?:"
    r"/(?:Users|private|var/folders|tmp|Volumes)/[^\n\r]*?"
    r"|[A-Z]:\\[^\n\r]*?"
    r"|\\\\[^\n\r]*?"
    r")\.(?:ai|pdf|png|jpg|jpeg|json|md|txt|yml|yaml)"
)

_GUARDRAILS = (
    "Private drawings/screenshots/raw reports stay out of git.",
    "PDF preview is not authoritative for AI-native Illustrator payloads.",
    "Posting/public proof is NO-GO unless W5/W7 accepts a public-safe packet.",
)


def build_visual_check_summary(
    subject: str | Path,
    *,
    before: str | Path | None = None,
    after: str | Path | None = None,
    diff: str | Path | None = None,
    report: str | Path | None = None,
    status: str = "needs_review",
    reviewer: str | None = None,
    issues: tuple[str, ...] | list[str] = (),
    notes: tuple[str, ...] | list[str] = (),
    opened_in_illustrator: bool = False,
) -> dict[str, Any]:
    """Build a local visual QA summary with every path reduced to a basename."""

    if status not in VALID_VISUAL_CHECK_STATUSES:
        valid = ", ".join(VALID_VISUAL_CHECK_STATUSES)
        raise ValueError(f"status must be one of: {valid}")

    summary: dict[str, Any] = {
        "schema_version": 1,
        "kind": "arch_lw_visual_check",
        "status": status,
        "artifacts": _artifact_payload(
            subject=subject,
            before=before,
            after=after,
            diff=diff,
            report=report,
        ),
        "issues": [_normalize_issue(issue) for issue in issues],
        "review": {
            "reviewer": _redact_local_paths(reviewer or ""),
            "opened_in_illustrator": bool(opened_in_illustrator),
            "accepted": status == "accepted",
            "requires_human_review": status != "accepted",
        },
        "notes": [_redact_local_paths(note) for note in notes],
        "posting_clearance": _posting_clearance(status),
        "next_step": _next_step(status),
        "guardrails": list(_GUARDRAILS),
    }
    _assert_no_local_paths(summary)
    return summary


def format_visual_check_markdown(summary: dict[str, Any]) -> str:
    """Format a visual-check summary as concise Markdown."""

    artifacts = summary.get("artifacts") if isinstance(summary.get("artifacts"), dict) else {}
    review = summary.get("review") if isinstance(summary.get("review"), dict) else {}
    issues = summary.get("issues") if isinstance(summary.get("issues"), list) else []
    notes = summary.get("notes") if isinstance(summary.get("notes"), list) else []
    guardrails = summary.get("guardrails") if isinstance(summary.get("guardrails"), list) else []

    lines = [
        "# arch-lw visual-check",
        "",
        f"Status: {summary.get('status', 'unknown')}",
        f"Subject: {artifacts.get('subject', '')}",
        f"Issues: {', '.join(str(issue) for issue in issues) if issues else 'none'}",
        f"Opened In Illustrator: {'yes' if review.get('opened_in_illustrator') else 'no'}",
        f"Accepted: {'yes' if review.get('accepted') else 'no'}",
    ]
    reviewer = review.get("reviewer")
    if reviewer:
        lines.append(f"Reviewer: {reviewer}")
    lines.extend(["", "Artifacts:"])
    for key in ("before", "after", "diff", "report"):
        value = artifacts.get(key)
        if value:
            lines.append(f"- {key}: {value}")
    lines.extend(
        ["", f"Posting: {summary.get('posting_clearance', '')}", f"Next step: {summary.get('next_step', '')}"]
    )
    if notes:
        lines.extend(["", "Notes:"])
        lines.extend(f"- {note}" for note in notes)
    if guardrails:
        lines.extend(["", "Guardrails:"])
        lines.extend(f"- {guardrail}" for guardrail in guardrails)
    text = "\n".join(lines).rstrip() + "\n"
    if _LOCAL_PATH_RE.search(text):
        raise ValueError("visual-check markdown contains a local/private path reference")
    return text


def open_in_illustrator(path: str | Path, *, app_name: str = "Adobe Illustrator") -> None:
    """Open a local drawing in Illustrator using macOS LaunchServices."""

    subprocess.run(["open", "-a", app_name, str(path)], check=False)


def _artifact_payload(
    *,
    subject: str | Path,
    before: str | Path | None,
    after: str | Path | None,
    diff: str | Path | None,
    report: str | Path | None,
) -> dict[str, str]:
    payload = {"subject": _basename(subject)}
    for key, value in (("before", before), ("after", after), ("diff", diff), ("report", report)):
        if value is not None:
            payload[key] = _basename(value)
    return payload


def _basename(value: str | Path) -> str:
    text = str(value).strip().removeprefix("file://").rstrip("/\\")
    parts = re.split(r"[\\/]", text)
    name = parts[-1].strip()
    return name or "artifact"


def _redact_local_paths(value: str) -> str:
    if not value:
        return ""
    return _LOCAL_PATH_WITH_EXT_RE.sub(lambda match: _basename(match.group(0)), str(value))


def _assert_no_local_paths(summary: dict[str, Any]) -> None:
    serialized = json.dumps(summary, sort_keys=True)
    if _LOCAL_PATH_RE.search(serialized):
        raise ValueError("visual-check summary contains a local/private path reference")


def _normalize_issue(issue: str) -> str:
    value = str(issue).strip()
    if not value:
        return value
    return value if value.startswith("#") else f"#{value}"


def _posting_clearance(status: str) -> str:
    if status == "accepted":
        return "SUMMARY-ONLY: redacted text can be linked; raw private proof remains NO-GO."
    if status == "rejected":
        return "NO-GO: visual QA rejected the output."
    if status == "blocked":
        return "NO-GO: visual QA is blocked."
    return "NO-GO: Illustrator visual acceptance is still pending."


def _next_step(status: str) -> str:
    if status == "accepted":
        return "Use this redacted summary as local evidence, or prepare a W5/W7 public packet if public proof is needed."
    if status == "rejected":
        return "Fix the failed visual regions, rerun the pipeline on a scratch copy, then review again in Illustrator."
    if status == "blocked":
        return "Resolve the blocker, keep private artifacts local, then rerun visual-check."
    return "Open the output in Illustrator, compare against before/proof views at print scale, and record accepted or rejected."
