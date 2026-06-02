"""Shared input-format sniffing and command diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pikepdf

KNOWN_COMMANDS = ("inspect", "apply", "apply-saas", "poche", "apply-jsx", "preview")
PDF_INPUT_KINDS = {
    "plain_pdf",
    "pdf",
    "pdf_compatible_ai",
    "illustrator_pdf",
    "pdf_compatible_ai_without_native_payload",
    "native_ai",
}


@dataclass(frozen=True)
class InputFormatDiagnostic:
    """Stable diagnostic payload for CLI and report surfaces."""

    path: str
    suffix: str
    header_kind: str
    input_kind: str
    container_kind: str
    command_support: Mapping[str, bool]
    command_support_reasons: Mapping[str, str | None]
    unsupported_reason: str | None = None
    suggested_next_step: str | None = None
    suffix_mismatch: bool = False
    is_no_op: bool | None = None
    has_drawings: bool | None = None
    no_drawing_reason: str | None = None
    pdf_error: str | None = None
    has_illustrator_pieceinfo: bool | None = None
    has_native_numblock: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON/report payload."""
        return {
            "path": self.path,
            "suffix": self.suffix,
            "header_kind": self.header_kind,
            "input_kind": self.input_kind,
            "container_kind": self.container_kind,
            "supported_commands": dict(self.command_support),
            "command_support": dict(self.command_support),
            "command_support_reasons": dict(self.command_support_reasons),
            "unsupported_reason": self.unsupported_reason,
            "suggested_next_step": self.suggested_next_step,
            "suffix_mismatch": self.suffix_mismatch,
            "is_no_op": self.is_no_op,
            "has_drawings": self.has_drawings,
            "no_drawing_reason": self.no_drawing_reason,
            "pdf_error": self.pdf_error,
            "has_illustrator_pieceinfo": self.has_illustrator_pieceinfo,
            "has_native_numblock": self.has_native_numblock,
        }


class UnsupportedInputError(ValueError):
    """Raised when a command cannot process the sniffed input."""

    def __init__(self, diagnostic: InputFormatDiagnostic):
        self.diagnostic = diagnostic
        message = diagnostic.unsupported_reason or "Input format is not supported."
        if diagnostic.suggested_next_step:
            message = f"{message} {diagnostic.suggested_next_step}"
        super().__init__(message)


def sniff_input(path: str | Path) -> InputFormatDiagnostic:
    """Return a command-agnostic diagnostic for *path*."""

    p = Path(path)
    suffix = p.suffix.lower()
    header = _read_header(p)
    header_kind = _header_kind(header)
    suffix_mismatch = _suffix_mismatch(suffix, header_kind)
    pdf_error = None

    if header_kind == "pdf":
        input_kind, has_illustrator_pieceinfo, has_native_numblock, pdf_error = _pdf_details(p, suffix)
        container_kind = "pdf"
        is_no_op = None
        has_drawings = None
        no_drawing_reason = None
    elif header_kind == "postscript":
        input_kind = "postscript_ai" if suffix == ".ai" else "postscript"
        container_kind = "postscript"
        is_no_op = None
        has_drawings = None
        no_drawing_reason = None
        has_illustrator_pieceinfo = None
        has_native_numblock = None
    elif header_kind == "empty":
        input_kind = "empty"
        container_kind = "empty"
        is_no_op = True
        has_drawings = False
        no_drawing_reason = "empty file"
        has_illustrator_pieceinfo = None
        has_native_numblock = None
    elif header_kind == "zip":
        input_kind = "zip"
        container_kind = "zip"
        is_no_op = None
        has_drawings = None
        no_drawing_reason = None
        has_illustrator_pieceinfo = None
        has_native_numblock = None
    else:
        input_kind = "unknown"
        container_kind = "unknown"
        is_no_op = None
        has_drawings = None
        no_drawing_reason = None
        has_illustrator_pieceinfo = None
        has_native_numblock = None

    support, reasons = _support_for(input_kind, suffix_mismatch=suffix_mismatch, pdf_error=pdf_error)
    return InputFormatDiagnostic(
        path=str(p),
        suffix=suffix,
        header_kind=header_kind,
        input_kind=input_kind,
        container_kind=container_kind,
        command_support=support,
        command_support_reasons=reasons,
        suffix_mismatch=suffix_mismatch,
        is_no_op=is_no_op,
        has_drawings=has_drawings,
        no_drawing_reason=no_drawing_reason,
        pdf_error=pdf_error,
        has_illustrator_pieceinfo=has_illustrator_pieceinfo,
        has_native_numblock=has_native_numblock,
    )


def diagnostic_for_command(path: str | Path, command: str) -> InputFormatDiagnostic:
    """Return the input diagnostic with command-specific guidance filled in."""

    command = _normalize_command(command)
    diag = sniff_input(path)
    if diag.command_support.get(command, False):
        return diag

    if diag.suffix_mismatch and diag.header_kind != "unknown":
        reason = _default_reason(diag)
    else:
        reason = diag.command_support_reasons.get(command) or _default_reason(diag)
    return replace(diag, unsupported_reason=reason, suggested_next_step=_suggested_next_step(diag, command))


def raise_if_unsupported(path: str | Path, command: str) -> InputFormatDiagnostic:
    """Return the diagnostic or raise :class:`UnsupportedInputError`."""

    diag = diagnostic_for_command(path, command)
    if not diag.command_support.get(_normalize_command(command), False):
        raise UnsupportedInputError(diag)
    return diag


def _read_header(path: Path) -> bytes:
    try:
        with path.open("rb") as f:
            return f.read(16)
    except FileNotFoundError:
        return b""


def _header_kind(header: bytes) -> str:
    if header == b"":
        return "empty"
    if header.startswith(b"%PDF"):
        return "pdf"
    if header.startswith(b"%!PS-Adobe"):
        return "postscript"
    if header.startswith(b"PK\x03\x04"):
        return "zip"
    return "unknown"


def _suffix_mismatch(suffix: str, header_kind: str) -> bool:
    if suffix in {".pdf", ".ai"}:
        if suffix == ".ai" and header_kind in {"pdf", "postscript", "empty"}:
            return False
        if suffix == ".pdf" and header_kind in {"pdf", "empty"}:
            return False
        return header_kind not in {"empty"}
    if suffix == ".zip":
        return header_kind != "zip"
    return False


def _pdf_details(path: Path, suffix: str) -> tuple[str, bool | None, bool | None, str | None]:
    try:
        with pikepdf.open(path) as pdf:
            page = pdf.pages[0] if len(pdf.pages) else None
            pieceinfo = page.obj.get("/PieceInfo") if page is not None else None
            illustrator = pieceinfo.get("/Illustrator") if isinstance(pieceinfo, pikepdf.Dictionary) else None
            private = illustrator.get("/Private") if isinstance(illustrator, pikepdf.Dictionary) else None
            has_pieceinfo = illustrator is not None
            has_numblock = isinstance(private, pikepdf.Dictionary) and "/NumBlock" in private
    except Exception as exc:
        return "pdf", None, None, f"{type(exc).__name__}: {exc}"

    if has_numblock:
        return "native_ai", has_pieceinfo, has_numblock, None
    if has_pieceinfo:
        return "pdf_compatible_ai_without_native_payload", has_pieceinfo, has_numblock, None
    if suffix == ".ai":
        return "pdf_compatible_ai", has_pieceinfo, has_numblock, None
    return "plain_pdf", has_pieceinfo, has_numblock, None


def _support_for(
    input_kind: str, *, suffix_mismatch: bool, pdf_error: str | None
) -> tuple[dict[str, bool], dict[str, str | None]]:
    if suffix_mismatch and input_kind != "unknown":
        reason = "File header does not match the file suffix."
        return (
            {command: False for command in KNOWN_COMMANDS},
            {command: reason for command in KNOWN_COMMANDS},
        )

    if pdf_error:
        reason = f"PDF header was found, but the file could not be opened as PDF ({pdf_error})."
        return (
            {command: False for command in KNOWN_COMMANDS},
            {command: reason for command in KNOWN_COMMANDS},
        )

    if input_kind in PDF_INPUT_KINDS:
        support = {command: True for command in KNOWN_COMMANDS}
        if input_kind != "native_ai":
            support["apply-saas"] = False
        if input_kind == "plain_pdf":
            support["apply-jsx"] = False
            support["poche"] = False
        reasons = {command: None for command in KNOWN_COMMANDS}
        native_reason = (
            "This .ai has no Illustrator native private payload (/NumBlock). "
            "apply-saas needs a native Illustrator .ai."
        )
        if input_kind != "native_ai":
            reasons["apply-saas"] = native_reason
        if input_kind == "plain_pdf":
            reasons["apply-jsx"] = (
                "Plain PDFs should use inspect/apply unless Illustrator layer preservation is required."
            )
            reasons["poche"] = "Plain PDFs do not preserve Illustrator cut-layer structure for poché."
        return support, reasons

    reason = _reason_for_input_kind(input_kind)
    return ({command: False for command in KNOWN_COMMANDS}, {command: reason for command in KNOWN_COMMANDS})


def _reason_for_input_kind(input_kind: str) -> str:
    if input_kind == "postscript_ai":
        return "Legacy PostScript .ai files are not supported."
    if input_kind == "postscript":
        return "PostScript files are not supported."
    if input_kind == "zip":
        return "ZIP containers are not supported."
    if input_kind == "empty":
        return "File is empty."
    return "File header is not recognized."


def _default_reason(diag: InputFormatDiagnostic) -> str:
    if diag.suffix_mismatch:
        suffix = diag.suffix or "(none)"
        return f"File header is {diag.header_kind.upper()} but suffix is {suffix}."
    return _reason_for_input_kind(diag.input_kind)


def _suggested_next_step(diag: InputFormatDiagnostic, command: str) -> str:
    if diag.input_kind in {"postscript_ai", "postscript"}:
        return "Open in Illustrator and Save As a PDF-compatible .ai or .pdf, then retry."
    if diag.input_kind == "empty":
        return "Choose a non-empty PDF-compatible .ai or .pdf file."
    if diag.input_kind == "unknown" or diag.suffix_mismatch:
        return "Check that the selected file is a PDF-compatible .ai or .pdf."
    if command == "apply-saas":
        return "For PDF-only/converted exports, use: arch-lw apply-jsx then arch-lw poche."
    if command == "poche":
        return "Run poché on layer-aware Illustrator output, usually after apply-jsx."
    return "Choose a supported PDF-compatible .ai or .pdf file."


def _normalize_command(command: str) -> str:
    normalized = command.replace("_", "-")
    aliases = {
        "apply-saas-poche": "poche",
        "poche-saas": "poche",
    }
    return aliases.get(normalized, normalized)
