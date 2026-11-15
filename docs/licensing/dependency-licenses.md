# Installed dependency licenses

Generated: 2026-11-15 with `importlib.metadata`.

Scope: project.dependencies and active transitive Requires-Dist; no root optional extras.
Environment: python_full_version=3.11.7, sys_platform=darwin, platform_machine=arm64.

Reproduce: `.venv/bin/python scripts/license_audit.py --format md --write`.
JSON evidence: [dependency-licenses.json](dependency-licenses.json).

AGPL/GPL/LGPL/SSPL flags screen declarations, not legal obligations. Alternatives and exceptions
remain in the license column. 'none detected' does not mean permissive: MPL and other licenses
are outside this flag set. UNKNOWN requires review. Long License fields are represented by
explicit declarations/titles, classifiers, and a SHA-256 digest in JSON, without full prose.
This is not a complete SBOM: native bundled libraries, license files, build/test/docs extras,
webapp-only and frontend dependencies, and the optional PDFium spike are outside this tree.
See [HOSTING.md](HOSTING.md) for the dated source review and limitations.

| Name | Version | License metadata / expression | License classifiers | Copyleft flag | Required by |
| --- | --- | --- | --- | --- | --- |
| click | 8.5.1 | BSD-3-Clause | not supplied | none detected | project |
| flatbuffers | 25.12.19 | Apache 2.0 | License :: OSI Approved :: Apache Software License | none detected | onnxruntime |
| lxml | 6.1.3 | BSD-3-Clause | not supplied | none detected | pikepdf |
| networkx | 3.6.1 | BSD-3-Clause | not supplied | none detected | pymupdf |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | not supplied | none detected | onnxruntime, project, pymupdf, scipy, shapely |
| onnxruntime | 1.32.0 | MIT License | License :: OSI Approved :: MIT License | none detected | pymupdf |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | not supplied | none detected | onnxruntime, pikepdf |
| pikepdf | 10.18.1 | MPL-2.0 | not supplied | none detected | project |
| pillow | 13.0.0 | MIT-CMU | not supplied | none detected | pikepdf, project |
| protobuf | 7.36.2 | 3-Clause BSD License | not supplied | none detected | onnxruntime |
| psutil | 7.2.2 | BSD-3-Clause | not supplied | none detected | pymupdf |
| pymupdf | 2.1 | AGPL-3.0 family; Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License | not supplied | AGPL | project, pymupdf-layout, pymupdf4llm |
| pymupdf-layout | 2.1 | UNKNOWN | not supplied | none detected | pymupdf, pymupdf4llm |
| pymupdf4llm | 2.1 | UNKNOWN | not supplied | none detected | pymupdf, pymupdf-layout |
| pyyaml | 6.0.3 | MIT | License :: OSI Approved :: MIT License | none detected | pymupdf |
| scipy | 1.17.1 | BSD-3-Clause; BSD-3-Clause-Open-MPI; GPL-3.0-or-later WITH GCC-exception-3.1; LGPL-2.1-or-later | License :: OSI Approved :: BSD License | LGPL, GPL | project |
| shapely | 2.2.0 | BSD-3-Clause | not supplied | none detected | project |
| tabulate | 0.10.0 | MIT | not supplied | none detected | pymupdf |
| zstandard | 0.25.0 | BSD-3-Clause | not supplied | none detected | project |

Review items: pymupdf-layout: missing license metadata; pymupdf4llm: missing license metadata.

Resolution errors: none.
