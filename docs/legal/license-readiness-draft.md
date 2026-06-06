# License Readiness Draft

Status: draft only. Do not merge an actual license swap from this document
without legal review and an approved release window.

This note supports GitHub issue #4. It does not change the repository license.
The live repository remains MIT-licensed through `LICENSE`, `pyproject.toml`,
README badges, and public docs until an approved legal change is merged.

## Current Facts

- Current source license file: `LICENSE` (MIT).
- Current package metadata: `pyproject.toml` uses `license = "MIT"` and
  `license-files = ["LICENSE"]`.
- Existing public docs still describe the core CLI as MIT-licensed.
- The published v1.0.0 artifact history noted in `docs/POSTMORTEM.md` says the
  license on already-downloaded copies cannot be clawed back retroactively.

## Proposed Future Direction

If legal approves the move, a future version may replace the MIT source license
with PolyForm Free Trial 1.0.0 plus a separate commercial EULA. The canonical
PolyForm Free Trial source is:

<https://polyformproject.org/licenses/free-trial/1.0.0>

Use the official plain-text license source at release time. Do not hand-edit the
PolyForm license text; the PolyForm project notes that modified versions must
remove PolyForm naming and project references.

## Required Legal Review Questions

- Is PolyForm Free Trial 1.0.0 the desired public source license for this
  product and business model?
- Does the commercial EULA need entity information, governing law, support
  promises, payment terms, export restrictions, privacy/data-processing terms,
  or architecture-client confidentiality terms?
- What happens to public examples, docs, tests, and prior MIT releases?
- Should the license change happen at v1.0.1, v1.1.0, or another explicit
  release boundary?
- What exact customer-facing purchase/trial language must match the EULA?

## Draft Files

- `docs/legal/DRAFT-LICENSE-PolyForm-Free-Trial-1.0.0.md`
- `docs/legal/DRAFT-COMMERCIAL-EULA.md`
- `docs/legal/DRAFT-METADATA-UPDATES.md`

These are readiness artifacts only. They are not legal advice and are not the
final license package.
