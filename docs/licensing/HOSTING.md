# Hosting and dependency review

**Draft for Zohar's review; not legal advice. Verify before any hosted launch.**

Reviewed 2026-11-15. These are draft statements for review, not approved terms or a launch decision.

## Three draft lines

1. PyMuPDF is used for preview rendering in `src/arch_line_weights/preview.py`, PDF inspection and fallback in `src/arch_line_weights/inspect.py`, and text/outline indexing in the standalone `scripts/build_reference_index.py`; the current webapp startup does not load it, and processing routes remain HTTP 410.
2. pypdfium2 is a possible preview replacement based on a small synthetic spike; pikepdf already handles basic inspection but is not a complete replacement for PyMuPDF's interpreted PDF drawings or text extraction. No replacement has been made.
3. For a future service where strangers upload files, review AGPL section 13's remote-user source offer and Artifex's stated requirement to disclose the whole combined application's source under AGPL, or obtain an Artifex commercial license; the exact covered service and Corresponding Source scope require review before hosting.

## Source evidence

- Installed distribution metadata, read with `importlib.metadata` on 2026-11-15:
  `pymupdf==2.1`, `License: Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License`.
  Neither `License-Expression` nor license classifiers were supplied. The audit flags the
  AGPL-3.0 family without choosing an SPDX `only`/`or-later` qualifier from that field.
- [Artifex licensing](https://artifex.com/licensing), accessed 2026-11-15:
  > If you can't meet the requirements of the GNU AGPLv3 above, a commercial license is required.

  Its Source Code Disclosure section states that server-based applications/services using
  its open-source software must disclose the application's full source under AGPL to users.
- [AGPL-3.0 section 13](https://www.gnu.org/licenses/agpl-3.0.html#section13), verified against
  [PyMuPDF's published COPYING text](https://github.com/pymupdf/PyMuPDF/blob/main/COPYING):
  the provision addresses a modified version that supports remote network interaction and
  requires a prominent opportunity for those users to obtain its Corresponding Source,
  free of charge, from a network server. What constitutes the covered/combined work in a
  particular service needs review; a dependency's presence alone does not establish that scope.
  A public MIT repository or a passing import test is not evidence of compliance with all terms.

| Proposed workflow | Observed distinction | Review before changing scope |
| --- | --- | --- |
| Local done-for-you work on Zohar's own machine, delivering drawing output | No customer-facing network processor in this workflow; software distribution is a separate question. | Confirm the actual use and any distribution obligations; this audit does not approve a business model. |
| Hosted upload/processing service for strangers | Would introduce remote interaction with a processing application. Current endpoints return HTTP 410. | Review source-offer coverage for the whole combined service and other AGPL terms, or an Artifex commercial license; a renderer spike does not remove the installed dependency. |

## Import paths and commands

Verified by source/AST inspection; no document indexing was run.

| Import site | Reachable commands | Use and qualification |
| --- | --- | --- |
| `src/arch_line_weights/preview.py:24` (`import pymupdf`) | `arch-lw preview`, all three modes, including `--ghostscript` | Eager module import; page counts/bounds and primary rasterization use PyMuPDF. Ghostscript selection still imports PyMuPDF and uses it for budget validation. |
| `src/arch_line_weights/inspect.py:175` (`import pymupdf`) | `arch-lw inspect`, `doctor`, `apply`, `apply-saas` | Lazy import in `_inspect_pdf`. Ordinary PDFs try it first; `.ai` and Illustrator-bearing PDFs try pikepdf first and can fall back to it. Inspection feeds dimensions, drawing counts, widths/colors, metadata and layer names. |
| `scripts/build_reference_index.py:25` (`import fitz`) | `python scripts/build_reference_index.py` and its standalone options; no `arch-lw` command | Eager legacy alias import; indexing reads page text and outlines. Source inspected only. |

The spike adds no direct PyMuPDF import: it calls the existing `PyMuPDFRenderer` through
`preview.py`. Existing `scripts/demo_gallery.py` and `scripts/visual_judge.py` also reach that
module; `scripts/benchmark.py` and `scripts/demo_gallery.py` call `inspect_file`.

The webapp's dormant `backend/compute.py` and `backend/console.py` still reference
`inspect_file`. The entry point currently imports the health router only. The new test
checks direct AST imports throughout `src/` and `webapp/`, plus a fresh-process import of
`webapp.backend.main`. It does not prove that arbitrary dynamic imports, future handlers,
or dormant pipeline calls cannot load PyMuPDF. The project still installs PyMuPDF.

## Installed dependency findings

See [the generated table](dependency-licenses.md) and [JSON evidence](dependency-licenses.json).
The core runtime tree contains 19 installed distributions in this snapshot:

- `pymupdf 2.1`: AGPL family / commercial alternative.
- `scipy 1.17.1`: its long metadata includes bundled `libgfortran`/`libgcc` declarations
  of `GPL-3.0-or-later WITH GCC-exception-3.1`, and a `libquadmath` declaration of
  `LGPL-2.1-or-later`. These are review flags, not a claim that SciPy's own BSD code is GPL
  or that every described binary is present in this wheel.
- `pikepdf 10.18.1`: `MPL-2.0`, a separate copyleft license outside the requested
  AGPL/GPL/LGPL/SSPL detector. It must not be described as Apache/BSD.
- `pymupdf-layout 2.1` and `pymupdf4llm 2.1`: license metadata absent; recorded as UNKNOWN.
  Their licenses must be checked separately before making claims about the complete stack.

This is the active Python runtime requirement tree, not a complete native binary or frontend
license inventory. Optional webapp/test/spike packages were installed only for local verification;
project manifests and lockfiles are unchanged. No commercial entitlement was verified.

## Replacement assessment and pending questions

The [renderer spike and inspection assessment](RENDERER-SPIKE.md) records the blank-fixture
limitation, visible control, timings, and remaining coverage gaps.

- Is the next offering local done-for-you work, distributed software, or hosted uploads?
- If hosting is planned, should review pursue an AGPL source-offer design, a commercial
  license, or a fully validated dependency replacement?
- Who will review combined-work/source scope, the two UNKNOWN packages, and bundled/native
  licenses before any hosted launch or licensing claim?

No Artifex contact, license purchase, dependency replacement, or hosting change was made.
