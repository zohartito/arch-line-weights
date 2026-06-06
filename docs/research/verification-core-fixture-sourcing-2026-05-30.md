# Verification Core Fixture Sourcing Research

Date: 2026-05-30

Scope: legal and practical fixture sources for a public verification corpus for
`arch-line-weights`. This is research only; no fixture assets are added here.

## Decision

Use a synthetic-first public corpus, backed by a private/local real-project
corpus and a very small number of public real-model fixtures only after license
review. The repo already says large private USC `.ai` samples are intentionally
not committed, so public verification should not depend on those files.

The verification core needs fixtures that cover input classes and failure modes
more than it needs impressive real drawings. Public real models are useful for
smoke and stress tests, but the risky edge cases are easier to make legal and
deterministic with authored synthetic inputs.

## Source Evidence

- Rhino Make2D documentation: Make2D projects selected geometry into flat 2D
  curve output, can maintain source layers, and has dedicated visible/hidden
  clipping-plane layer options.
  <https://docs.mcneel.com/rhino/mac/help/en-us/commands/make2d.htm>
- McNeel Bongo sample models: official `.3dm` downloads exist, but the visible
  page carries McNeel copyright and no explicit redistribution license.
  <https://www.rhino3d.com/plugins/bongo/docs/sample-models/>
- McNeel Rhino in Architecture course: official course page provides a PDF and
  source files ZIP for architecture workflows.
  <https://wiki.mcneel.com/training/rhino_for_arch/rhino_in_architecture_course>
- McNeel Rhino in Architecture PDF: the visible copyright notice allows personal
  or classroom copying without profit, but republishing, server posting, or
  list redistribution requires prior permission.
  <https://wiki.mcneel.com/_media/training/rhino_for_arch/rhinoceros_in_architecture_course.pdf>
- Rhino 8 Section Styles demo: official page links a `SectionStyles-Demo.3dm`
  model, but no explicit redistribution license is visible on the page.
  <https://www.rhino3d.com/en/features/clipping/section-styles/>
- BlockTool: public architectural Rhino/Grasshopper demo with `Demo_Site.3dm`;
  GitHub labels the repository MIT.
  <https://github.com/BlockTool/BlockTool>
- WikiHouse Wren: public architectural Grasshopper system; repository text says
  the Grasshopper file is licensed under MPL 2.0 and the repo was archived on
  2026-05-05.
  <https://github.com/wikihouseproject/Wren>
  <https://www.mozilla.org/en-US/MPL/2.0/>
- NYC 3D Building Model metadata: public dataset in Rhino-compatible `.3dm`
  format, subdivided by community district, with building and linework layers.
  <https://www.nyc.gov/assets/planning/download/pdf/data-maps/open-data/nyc-3d-model-metadata.pdf>
- NYC Open Data FAQ: says Open Data has no restrictions on use, with Terms of
  Use still applicable.
  <https://opendata.cityofnewyork.us/faq/>
- NYC Open Data technical standards: says public datasets should be available
  without registration, license, or usage restrictions except as provided, and
  may require source/version/modification identification when republished.
  <https://cityofnewyork.github.io/opendatatsm/publicpolicies.html>
- Playwright visual comparisons: reference screenshots are generated, committed,
  and compared on later runs; rendering environment differences matter.
  <https://playwright.dev/docs/next/test-snapshots>
- pytest-mpl image comparison: baseline images should be generated, inspected,
  committed, and compared with tolerance-aware test runs.
  <https://pytest-mpl.readthedocs.io/en/latest/image_mode.html>
- rhino3dm: MIT-licensed library for reading/writing `.3dm` files independent
  of Rhino, useful for synthetic fixture generation where Make2D itself is not
  required.
  <https://github.com/mcneel/rhino3dm>

## Ranked Fixture Sources

1. Synthetic fixtures authored in this repo

   License posture: safest. Project-authored source and generated outputs can
   be MIT with the repo.

   Use for public CI and exact edge cases: native AI-private payload with
   `/NumBlock`, PDF-backed `.ai`, plain PDF, legacy PostScript-like `.ai`,
   empty file, ZIP-like mislabeled file, document PDF, broken Make2D loops,
   helper-only fragments, and poché confidence boundaries.

   Recommendation: make this the public corpus foundation.

2. Local private real-project fixtures

   License posture: safe only if kept local and ignored. Do not commit raw
   files, screenshots, rendered baselines, or project-identifying layer names.

   Use for dogfood verification: USC section proof, axon stress file, and
   legacy Rhino PostScript exports. Store only aggregate metrics, hashes, and
   redacted manifests in the repo if needed.

3. BlockTool demo site

   License posture: promising. Repository is marked MIT and includes a Rhino
   `demo/3D Model/Demo_Site.3dm` path in the README. Confirm the MIT license
   covers binary/demo assets before committing any derived output.

   Use for public real fixture: facade/elevation/massing Make2D smoke with
   ordinary architectural layers, not detailed section poché.

4. NYC 3D Building Model

   License posture: promising but attribution-heavy. Metadata says the model is
   a public dataset in `.3dm` format; NYC Open Data FAQ says no restrictions,
   while the standards manual says source/version/modification identification
   may be required for republishing.

   Use for public real fixture: a clipped, tiny community-district extract for
   massing/elevation/axon line hierarchy. It is not a wall-section or poché
   fixture.

5. WikiHouse Wren

   License posture: usable with care. The repo states MPL 2.0 for the
   Grasshopper file and includes additional terms of use/no-warranty language.
   MPL is compatible with public research use but adds file-level obligations
   that are less frictionless than MIT or city open data.

   Use for public real fixture only if the project accepts MPL attribution and
   source availability obligations for any included source files. Prefer
   generated outputs plus clear attribution over vendoring the original `.gh`.

6. McNeel official sample and training models

   License posture: useful for local/manual testing but not safe for public
   committed fixtures without permission. Bongo, Section Styles, and training
   files are official and downloadable, but the visible pages do not grant a
   broad open-source redistribution license. The architecture PDF explicitly
   limits redistribution.

   Use locally to understand real Rhino output patterns; do not commit raw
   models or derived baselines until permission is clear.

7. Other open-source Rhino/Grasshopper repositories

   License posture: case-by-case. Some repositories are MIT or permissive, but
   many do not clearly license binary `.3dm` or `.gh` assets separately from
   code.

   Use only after verifying the exact asset path, license file, and whether the
   binary model is covered by the repo license.

8. Forum attachments, Food4Rhino examples, tutorial downloads with unclear
   terms

   License posture: avoid for public fixtures. They may be fine to download and
   learn from personally, but they are poor release-gate assets unless the
   author gives explicit redistribution permission.

## Recommended Initial Corpus

### Public Synthetic Fixtures

1. `syn-ai-native-section-wall-openings-numblock`
   - Input: minimal native Illustrator `.ai` with `/NumBlock`.
   - Covers: AI-private path, layer preservation, native section poché.
   - Expected behavior: pass, generated poché only for high-confidence cut
     regions.

2. `syn-ai-converted-section-wall-openings-jsx`
   - Input: PDF-only or converted `.ai` without `/NumBlock`.
   - Covers: Illustrator bridge path, then poché on bridge output.
   - Expected behavior: pass through bridge workflow; direct native-payload
     poché should explain missing `/NumBlock`.

3. `syn-pdf-axon-layered-line-hierarchy`
   - Input: plain vector PDF with linework colors and layer-like structure where
     possible.
   - Covers: general PDF stream path and visual diff of hierarchy changes.
   - Expected behavior: pass for line-weight hierarchy, no section poché claim.

4. `syn-ai-legacy-postscript-unsupported`
   - Input: tiny text fixture beginning with `%!PS-Adobe`.
   - Covers: legacy Rhino/PostScript `.ai` clean unsupported-input diagnostics.
   - Expected behavior: fail cleanly with re-save/conversion next action; no PDF
     parser traceback.

5. `syn-pdf-poche-ambiguous-helper-geometry`
   - Input: broken Make2D-style loops, short fragments, helper-only geometry,
     gaps, and window/opening islands.
   - Covers: conservative poché and confidence reporting.
   - Expected behavior: fill only high-confidence closed structural regions;
     leave ambiguous geometry for review.

### Private Local Fixtures

1. `local-usc-section-converted-wall`
   - Source: existing USC wall section converted `.ai`.
   - Covers: real section proof path: bridge hierarchy, then poché.
   - Public rule: never commit raw file, screenshots, exported output, or
     identifying layer names.

2. `local-usc-axon-native-macro`
   - Source: existing 98 MB / 1.28M-stroke axon stress file.
   - Covers: performance and native payload rewrite on a huge real drawing.
   - Public rule: keep local only; publish only aggregate timing/stroke counts.

3. `local-rhino-legacy-postscript-ai`
   - Source: one or more legacy Rhino PostScript `.ai` exports from the private
     validation corpus.
   - Covers: clean unsupported diagnostics and conversion guidance.
   - Public rule: use copies only, dry-run where possible, never commit.

### Public Real Fixtures If Safe

1. `pub-blocktool-demo-site-make2d-elevation`
   - Source: BlockTool `Demo_Site.3dm`.
   - License note: MIT repo, but confirm binary/demo asset coverage before
     committing generated outputs.
   - Use: small Make2D elevation or facade smoke fixture.

2. `pub-nyc-3d-model-community-district-axon`
   - Source: NYC 3D Building Model, clipped to the smallest useful extract.
   - License note: public dataset; retain NYC Planning/Open Data attribution,
     source URL, version/date, and modification notes.
   - Use: line hierarchy, massing, stress, and layer robustness. Not a section
     poché fixture.

Alternative public-real choice: replace NYC with WikiHouse Wren if section-like
architectural geometry matters more than license simplicity. That requires MPL
2.0 attribution/source handling.

## Fixture Naming Scheme

Use:

```text
{visibility}-{source}-{format}-{geometry}-{case}-{variant}
```

Where:

- `visibility`: `syn`, `pub`, `local`
- `source`: `internal`, `blocktool`, `nyc`, `wren`, `usc`
- `format`: `ai-native`, `ai-converted`, `ai-ps`, `pdf`, `3dm`
- `geometry`: `section`, `axon`, `elevation`, `document`, `container`
- `case`: `line-hierarchy`, `poche`, `unsupported`, `empty`, `mislabeled`
- `variant`: concise distinguishing tag, such as `numblock`,
  `no-numblock`, `openings`, `zip-header`

Examples:

- `syn-internal-ai-native-section-poche-numblock`
- `syn-internal-ai-converted-section-poche-no-numblock`
- `syn-internal-ai-ps-section-unsupported-legacy`
- `pub-blocktool-3dm-elevation-line-hierarchy-demo-site`
- `pub-nyc-3dm-axon-line-hierarchy-community-district`
- `local-usc-ai-converted-section-poche-private`

Recommended directory layout if this becomes code:

```text
tests/fixtures/public/{fixture_id}/
tests/fixtures/public/{fixture_id}/manifest.json
tests/fixtures/public/{fixture_id}/source/
tests/fixtures/public/{fixture_id}/expected/
tests/fixtures/private-local/     # gitignored
tests/baseline-images/{fixture_id}/
```

## Manifest Fields

Required fields:

- `fixture_id`
- `visibility`: `synthetic`, `public`, or `private-local`
- `input_format_class`: `native_numblock_ai`, `pdf_backed_ai`,
  `plain_pdf`, `legacy_postscript_ai`, `document_pdf`,
  `zip_like_container`, `empty_file`, `unknown`
- `source_url`
- `source_owner`
- `source_license`
- `license_url`
- `redistribution_allowed`: `yes`, `no`, or `unknown`
- `attribution_required`
- `attribution_text`
- `source_file_sha256`
- `source_file_bytes`
- `derived_from`
- `generation_command`
- `generator_version`
- `rhino_version`
- `illustrator_version`
- `export_workflow`: `make2d_pdf`, `native_ai_save`,
  `converted_ai_bridge`, `plain_pdf`, `synthetic_bytes`
- `expected_behavior`: `pass`, `warn`, or `fail_cleanly`
- `expected_cli_path`
- `expected_exit_code`
- `expected_metrics`: modified paths, layer count, poché polygons, failed
  layers, warnings, timing ceiling where relevant
- `baseline_artifacts`: expected PDF/PNG/JSON paths plus SHA256 values
- `known_caveats`
- `private_reason`
- `last_verified_at`
- `verified_by`
- `review_status`

## Visual Regression Practice

Comparable projects commit small baseline artifacts and compare future output to
them. Playwright treats the first stable screenshot as a reference image, then
compares subsequent runs and expects the snapshot folder to be committed.
pytest-mpl similarly recommends generating baseline images, inspecting them,
and committing them before running image comparison tests.

For this project:

- Commit only small public/synthetic baseline images and JSON summaries.
- Store baselines per fixture and renderer environment.
- Pin or record renderer versions for PDF-to-image comparisons.
- Require human review when updating baselines.
- Keep private/local fixture baselines outside the repo.

## What Must Never Be Committed Publicly

- USC, studio, client, professor, or course project source drawings.
- Derived `.ai`, `.pdf`, `.3dm`, screenshots, visual baselines, or layer dumps
  from private drawings.
- Project-identifying layer names, material codes, file names, or title-block
  details from private drawings.
- McNeel sample/training models or derived baselines unless explicit
  redistribution permission is obtained.
- Copyrighted reference books, scanned pages, traced details, or rendered
  excerpts from private reference material.
- Forum attachments, Food4Rhino examples, or tutorial downloads where the
  asset license is unclear.
- Public datasets without required attribution, source URL, version/date, and
  modification notes.
- Any fixture whose manifest says `redistribution_allowed: no` or `unknown`.
- Bluebeam proof assets until Bluebeam behavior is actually verified and the
  source fixture is legal to publish.

## License Closure Notes

### BlockTool `Demo_Site.3dm`

Status: conditionally usable for public fixtures.

Evidence:

- The repository README instructs users to open
  `demo/3D Model/Demo_Site.3dm`.
  <https://github.com/BlockTool/BlockTool>
- GitHub labels the repository with the MIT license.
  <https://github.com/BlockTool/BlockTool>
- GitHub's own license API documentation warns that repository license
  detection matches a root license file and does not account for dependencies
  or other ways a project may document license terms.
  <https://docs.github.com/en/rest/licenses/licenses?apiVersion=2022-11-28>

Interpretation: the best available public signal is that BlockTool is MIT and
the demo `.3dm` is part of the same repository. That is good enough for a
small public fixture after a final checkout-level review confirms there is no
asset-specific license or third-party data notice under `demo/` or `media/`.
Keep the source URL, repository license, commit SHA, and attribution in the
fixture manifest. Do not claim this is legal advice.

### NYC 3D Building Model

Status: usable for a public real fixture with attribution and size control.

Evidence:

- The NYC metadata describes the model as a public dataset and says it was
  converted into `.3dm` format compatible with Rhino.
  <https://www.nyc.gov/assets/planning/download/pdf/data-maps/open-data/nyc-3d-model-metadata.pdf>
- The same metadata identifies credits/stewards and use limitations.
  <https://www.nyc.gov/assets/planning/download/pdf/data-maps/open-data/nyc-3d-model-metadata.pdf>
- NYC Open Data FAQ says Open Data has no restrictions on use, while pointing
  readers to the Terms of Use.
  <https://opendata.cityofnewyork.us/faq/>
- NYC's open data technical standards say public datasets should be available
  without registration, license, or usage restrictions except as provided, and
  that republishers may need to identify source, version, and modifications.
  <https://cityofnewyork.github.io/opendatatsm/publicpolicies.html>

Interpretation: NYC is the best public real-model candidate. Use the smallest
possible clipped extract and manifest the source as NYC Planning / NYC Open
Data, including dataset name, source URL, download date, source version/date,
modification notes, and no-warranty/use-limitation text. Prefer generated
Make2D/PDF outputs over committing full community-district `.3dm` files.

### WikiHouse Wren

Status: usable but not recommended for the first public corpus.

Evidence:

- The Wren README says the repository's Grasshopper file was developed by
  Architecture 00 and is licensed under MPL 2.0.
  <https://github.com/wikihouseproject/Wren>
- MPL 2.0 grants rights to use, reproduce, make available, modify, display,
  perform, distribute, and otherwise exploit contributions, but its conditions
  include source-form distribution and notice obligations for covered software.
  <https://www.mozilla.org/en-US/MPL/2.0/>

Interpretation: Wren can be used if the project is ready to carry MPL notices
and source-availability obligations for any covered files that are distributed.
It is a good second-wave architectural fixture, especially for section-like
building geometry, but the first public corpus should avoid MPL complexity
unless BlockTool/NYC fall through.

### McNeel Sample And Training Files

Status: local-only unless explicit permission is obtained.

Evidence:

- McNeel's Bongo page provides official sample `.3dm` downloads but shows
  McNeel copyright and no broad redistribution license on the visible page.
  <https://www.rhino3d.com/plugins/bongo/docs/sample-models/>
- Rhino's Section Styles page links `SectionStyles-Demo.3dm`, but the visible
  page shows McNeel copyright and no open redistribution license.
  <https://www.rhino3d.com/en/features/clipping/section-styles/>
- The Rhino in Architecture course provides class materials and source files.
  <https://wiki.mcneel.com/training/rhino_for_arch/rhino_in_architecture_course>
- The course PDF's visible copyright notice allows personal/classroom copying
  without profit but requires prior permission for republishing, server posting,
  or redistribution to lists.
  <https://wiki.mcneel.com/_media/training/rhino_for_arch/rhinoceros_in_architecture_course.pdf>

Interpretation: McNeel files are good local reference material for learning how
official sample models export through Rhino/Make2D. They should not be
committed, nor should derived visual baselines be committed, without a written
license or permission that explicitly allows public redistribution in this
repository.

### rhino3dm Synthetic Fixture Path

Status: safe and recommended for synthetic source fixtures.

Evidence:

- `rhino3dm` is MIT-licensed.
  <https://github.com/mcneel/rhino3dm>
- Its README says it can create, interrogate, store, read, and write Rhino
  geometry and non-geometry classes such as layers, object attributes,
  transforms, and viewports independent of Rhino.
  <https://github.com/mcneel/rhino3dm>

Interpretation: use `rhino3dm` for authored `.3dm` source fixtures where the
test does not need Rhino's Make2D implementation itself. For Make2D-specific
fixtures, still generate the exported `.ai` or `.pdf` deterministically and
commit only tiny project-authored outputs.

## Public Fixture Go/No-Go

| Candidate | Public commit decision | Notes |
| --- | --- | --- |
| Project-authored synthetic `.ai` / `.pdf` / tiny `.3dm` | GO | Safest path. MIT with this repo. |
| BlockTool `Demo_Site.3dm` derived Make2D output | GO after final asset-license check | Repo-level MIT signal is strong; still verify no asset-specific exception before adding. |
| NYC 3D Building Model clipped extract or derived output | GO with attribution | Best public real-model source. Keep it tiny and document source/version/modifications. |
| WikiHouse Wren derived output | DEFER | Usable under MPL 2.0, but not first corpus because of notice/source obligations. |
| McNeel Bongo / Section Styles / Architecture course files | NO-GO for public repo | Local-only unless McNeel grants redistribution permission. |
| USC/private real drawings and derivatives | NO-GO for public repo | Local-only. Publish only redacted aggregate metrics. |
| Forum/Food4Rhino/tutorial attachments with unclear terms | NO-GO | Use only with explicit permission. |

## Recommended First Public Corpus

Build the first public corpus in this order:

1. `syn-internal-ai-native-section-poche-numblock`
   - Project-authored native Illustrator `.ai` with `/NumBlock`.
   - Covers `apply-saas --poche` on native payload inputs.

2. `syn-internal-ai-converted-section-poche-no-numblock`
   - Project-authored converted/PDF-backed `.ai`.
   - Covers `apply-jsx`, then `arch-lw poche` on the bridge output.

3. `syn-internal-pdf-axon-line-hierarchy-layered`
   - Project-authored vector PDF.
   - Covers line-weight hierarchy without section/poché claims.

4. `syn-internal-ai-ps-unsupported-legacy`
   - Tiny `%!PS-Adobe` legacy `.ai` fixture.
   - Covers clean unsupported-input diagnostics.

5. `syn-internal-pdf-poche-ambiguous-helper-geometry`
   - Project-authored broken-loop section fixture.
   - Covers conservative poché confidence boundaries.

6. `pub-nyc-3dm-axon-line-hierarchy-clipped`
   - Tiny NYC Open Data-derived extract or Make2D output.
   - Covers real public urban/massing linework and layer robustness.

7. `pub-blocktool-3dm-elevation-line-hierarchy-demo-site`
   - Small BlockTool-derived Make2D output after final asset-license check.
   - Covers real public architectural/facade geometry.

This keeps the first corpus legal-first while still including two public real
fixtures. Wren remains a second-wave candidate if stronger architectural
section geometry is needed and MPL handling is acceptable.

## Private Fixture Handling Rules

- Keep private fixtures under a local gitignored path, not under
  `tests/fixtures/public`.
- Do not record private source filenames in committed manifests. Use stable
  local aliases such as `private-section-proof-a`, `private-axon-stress-a`, and
  `private-legacy-ai-a`.
- Do not commit rendered images, PDFs, `.ai` outputs, layer dumps, title blocks,
  or screenshots from private drawings.
- Only commit aggregate metrics that are already public-safe: file size class,
  stroke count, command path, exit code, timing, number of modified paths,
  layer count, poché polygon count, and failed-layer count.
- If hashes are useful, keep full hashes local. Public docs may use short
  redacted identifiers only when they cannot be linked back to a private file.
- Private verification should run on copies or dry-run outputs where possible.
- Public claims must say "validated on private fixtures" only at the aggregate
  level and must not imply those fixtures are available in the repo.

## Follow-Up Checklist

- Perform a checkout-level BlockTool review for any asset-specific license or
  third-party data notice before adding a derived public fixture.
- Pick one NYC community district and create the smallest legally attributable
  clipped public fixture if size is reasonable.
- Draft synthetic fixture generators before importing any third-party model.
- Add a manifest schema before adding fixture files.
- Keep private validation fixtures under a gitignored local path with redacted
  aggregate reporting only.
