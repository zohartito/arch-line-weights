# Ship Checklist

## Ready for Cursor 1 Dogfood

- [x] Current checkout is a local source checkout; do not publish local machine paths.
- [x] Day-1 CLI path documented: `.venv/bin/arch-lw`.
- [x] Public install path documented as source/GitHub install, not PyPI.
- [x] `arch-lw apply --preset usc` is supported.
- [x] `arch-lw apply-saas --preset usc` is supported.
- [x] README explains that basic `apply` is fast stroke-weight output.
- [x] README explains that `apply-saas --architectural --poche --preset usc --source rhino` is a local review path for Rhino 8 -> Illustrator `.ai` -> Illustrator/Acrobat inspection.
- [x] Tiny tracked PDF fixture added at `examples/sample-linework.pdf`.
- [x] `examples/sample-mapping.json` is pure `RGB(...) -> weight` JSON.
- [x] `CONVENTIONS.md` integrated into the repository root.
- [x] USC public print texture/hatch convention is 0.13 mm; 0.08 pt remains screen-review only.
- [x] Webapp/frontend documented as experimental local scaffold only.

## Needs Zohar Decision Before Public v1

- [ ] Global install story: the QA shell does not have `arch-lw`, `uv`, or `uvx` on `PATH`. Decide whether public v1 should stay GitHub/source-first, use `pipx install git+https://github.com/zohartito/arch-line-weights`, or wait for PyPI.
- [ ] PyPI publish: README intentionally says PyPI is not published yet. Decide whether v1 launch requires a real `pip install arch-line-weights` path.
- [ ] Real sample fixture: large USC `.ai` drawings remain excluded from git. Decide whether to add a small anonymized `.ai`, use Git LFS/private release assets, or keep only the tiny PDF smoke fixture.
- [ ] Bluebeam QA: Bluebeam is Windows-only/unverified for this Mac dogfood. Decide whether it is in scope for public v1 or deferred.
- [ ] PC mirror verification: `ssh desktop-zt` did not resolve from this Mac session, so the Windows/Synology copy still needs an external check when that hostname is reachable.
- [ ] Frontend/SaaS hardening: webapp remains local-only and experimental for this push.

## Current Recommended Dogfood Command

```bash
cd path/to/arch-line-weights
.venv/bin/arch-lw inspect path/to/rhino-export.ai
.venv/bin/arch-lw apply-saas path/to/rhino-export.ai \
  --architectural --poche --preset usc --source rhino
```
