# Repository Recovery Runbook

Date: 2026-06-04

This note records the workflow that recovered the May 2026 local
`arch-line-weights` work and pushed it back to GitHub without losing data.
Use it whenever Synology, Google Drive, branch drift, or multi-machine work
creates competing project copies.

## Goal

Recover one authoritative project tree, preserve every candidate copy until
the user confirms cleanup, and push only intentional source/docs changes to
GitHub.

The correct pattern is:

```text
inventory all copies
-> identify git state and newest real source
-> create a separate reconciled tree
-> clone GitHub fresh
-> overlay recovered work without deleting GitHub-only files
-> inspect risky files
-> verify
-> commit and push
-> verify remote pushedAt and branch hash
```

## Case Study: 2026-05-30

Problem:

- GitHub was stale by about three weeks.
- `~/SynologyDrive/Projects/` had three fragmented copies:
  `arch-line-weights`, `arch-line-weights_1`, and `arch_line_weights`.
- None of those folders had a `.git` directory.
- The PC copy over Tailscale had the same fragments.
- Generated debris existed in several places: `site*`, `dist*`,
  `*.egg-info`, caches, and private reference data.

Finding:

- `arch-line-weights_1` was the authoritative source tree.
- The Mac and PC `arch-line-weights_1` copies matched by file hash.
- The smaller `arch-line-weights` fragment contained only a few orphan files
  plus generated output.
- `arch_line_weights` did not contain real non-generated project files.

Outcome:

- A fresh clone was created at `~/projects/arch-line-weights-git`.
- Recovered work was overlaid without `--delete`.
- GitHub-only files such as `.github/`, `.gitignore`, docs settings, and webapp
  placeholders were preserved.
- Private/generated data stayed out of Git.
- Commit `31e314c7593d8f7bacc7338004454c19c5f2c997` was pushed to `main`.
- Verification after push: `521 passed, 1 skipped`; `arch-lw --version`
  reported `1.0.1.dev34+g31e314c75`.

## Inventory Commands

Start by checking the obvious local fragments:

```bash
for d in \
  ~/SynologyDrive/Projects/arch-line-weights \
  ~/SynologyDrive/Projects/arch-line-weights_1 \
  ~/SynologyDrive/Projects/arch_line_weights
do
  echo "== $d =="
  ls "$d"
  git -C "$d" status 2>&1 | head -3
done
```

Check whether any nested copy has a real Git repository:

```bash
find ~/SynologyDrive/Projects -maxdepth 3 -type d -name .git
```

Search for other local copies before assuming the three obvious folders are the
whole story:

```bash
find ~ -maxdepth 5 \
  \( -type d -name 'arch-line-weights*' -o -type d -name 'arch_line_weights*' \) \
  -print 2>/dev/null
```

If a Windows desktop is part of the workflow, check it too:

```bash
ssh desktop-zt 'wsl bash -lc "
  ls -la /mnt/c/Users/zohar_4ta16fp/SynologyDrive/Projects/arch-line-weights &&
  git -C /mnt/c/Users/zohar_4ta16fp/SynologyDrive/Projects/arch-line-weights status 2>&1 | head
"'
```

## Compare Real Work, Not Generated Debris

Ignore generated or private artifacts when deciding which tree is newer:

- `dist/`, `dist_*`
- `site/`, `site_*`
- `*.egg-info`
- `__pycache__/`
- `.pytest_cache/`, `.ruff_cache/`
- `.venv/`
- `data/reference_books/`
- `references/source-books/`
- `*.sqlite`, `*.sqlite3`, `*.sqlite-shm`, `*.sqlite-wal`
- raw `.ai`, `.3dm`, `.pdf` samples unless explicitly intended for Git LFS

Useful quick inventory:

```bash
find "$candidate" -type f \
  ! -path '*/dist/*' ! -path '*/dist_*/*' \
  ! -path '*/site/*' ! -path '*/site_*/*' \
  ! -path '*/*.egg-info/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/.venv/*' \
  ! -path '*/data/reference_books/*' \
  ! -path '*/references/source-books/*' \
  | wc -l
```

For Mac/PC comparison, make a hash manifest of real files and diff the
manifests. Matching manifests mean the copies are equivalent and the Mac copy
can be used locally.

## Build A Reconciled Tree

Never reconcile in place. Create a new clean working tree:

```bash
RECON=~/projects/arch-line-weights-reconciled
rm -rf "$RECON"
mkdir -p "$RECON"

rsync -a \
  --exclude='.git' \
  --exclude='dist' --exclude='dist_*' \
  --exclude='site' --exclude='site_*' \
  --exclude='*.egg-info' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='data/reference_books' \
  --exclude='references/source-books' \
  --exclude='*.sqlite' --exclude='*.sqlite3' \
  --exclude='*.sqlite-shm' --exclude='*.sqlite-wal' \
  "$AUTHORITATIVE_COPY/" "$RECON/"
```

If a smaller fragment has orphan files, preserve them for review instead of
committing them blindly:

```bash
mkdir -p "$RECON/_recovered_conflict_review/main_fragment"
```

Put odd files there with their original paths. Examples from the May recovery:

- `-.png`
- older one-off spike scripts
- generated-looking files that need human review

## Clone GitHub Fresh

Use a fresh clone as the commit target:

```bash
gh repo clone zohartito/arch-line-weights ~/projects/arch-line-weights-git
cd ~/projects/arch-line-weights-git
git status --short --branch
git log --oneline -5
```

This avoids trusting a folder that might not have `.git`, might be stale, or
might have Synology conflict copies mixed into it.

## Overlay, Do Not Delete

The most important lesson from the recovery: do not use a deleting sync from a
fragment onto the fresh GitHub clone.

Bad pattern:

```bash
rsync -a --delete "$RECON/" "$GIT/"
```

Why it is dangerous:

- Local fragments often miss GitHub-only files.
- A delete sync can remove `.github/`, `.gitignore`, docs config, issue
  templates, webapp placeholders, benchmark files, and other legitimate repo
  metadata.
- Missing from a fragment does not mean deleted intentionally.

Good pattern:

```bash
rsync -a \
  --exclude='.git' \
  --exclude='dist' --exclude='dist_*' \
  --exclude='site' --exclude='site_*' \
  --exclude='*.egg-info' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='_recovered_conflict_review' \
  --exclude='data/reference_books' \
  --exclude='references/source-books' \
  --exclude='*.sqlite' --exclude='*.sqlite3' \
  --exclude='*.sqlite-shm' --exclude='*.sqlite-wal' \
  "$RECON/" "$GIT/"
```

Then inspect:

```bash
git status --short --ignored
git diff --stat
git diff --name-status
```

## Risk Review Before Commit

Before staging, classify every changed file:

| File type | Default decision |
|---|---|
| `src/` source | inspect and commit if intentional |
| `tests/` | inspect and commit if they cover recovered behavior |
| `docs/` | inspect and commit if derived/original |
| one-off `scripts/spike/` | commit only if useful and clearly a spike |
| `uv.lock` or lockfiles | commit if the project expects reproducible installs |
| raw `.ai`, `.3dm`, `.pdf` | do not commit by default |
| source books or extracted pages | never commit |
| SQLite reference DBs | never commit |
| `site/`, `dist/`, egg-info, caches | never commit |
| strange orphan files | preserve in review folder, do not commit blindly |

Also search for secrets:

```bash
git diff --cached
rg -n "api[_-]?key|token|secret|password|ANTHROPIC|OPENAI|gho_" .
```

## Verification Gate

Use fresh evidence before saying the repo is recovered.

Minimum local gate:

```bash
python -m pip install -e .
python -m pytest
python -m ruff check src tests
arch-lw --version
```

For this project, if a spike script is part of the staged diff, include it in
the lint command:

```bash
python -m ruff check src tests scripts/spike/rebuild_stairs_cohesive_flights.py
```

If the repo is in deadline mode and GitHub Actions minutes are tight, local
verification is the primary gate. Do not rely on hosted CI to discover obvious
problems after pushing.

## Commit And Push

Stage only intended files:

```bash
git add path/to/file1 path/to/file2
git status --short --branch
git diff --cached --stat
git diff --cached --name-status
```

Commit with a message that says what was recovered and why:

```bash
git commit -m "Recover local line-weight ladder and stair research"
```

Push:

```bash
git push origin "$(git branch --show-current)"
```

Verify the remote:

```bash
gh repo view zohartito/arch-line-weights --json pushedAt,defaultBranchRef,url
git rev-parse HEAD
git ls-remote origin "refs/heads/$(git branch --show-current)"
```

Only after that should the user decide whether old fragments are safe to
delete.

## Cleanup Policy

The agent should not delete original Synology fragments automatically.

Report:

- authoritative copy
- fragments compared
- files recovered
- files intentionally not committed
- commit hash
- push confirmation
- verification results
- folders that are likely safe for the user to delete

Recommended hold period:

- Keep the fresh Git clone.
- Keep the reconciled snapshot for a short time.
- Delete Synology conflict fragments only after GitHub and local tests are
  verified and the user confirms.

## Agent Behavior Checklist

Use this checklist for future recovery sessions:

- Announce the current phase before making changes.
- Prefer `rg` and `find` for inventory.
- Use fresh clones and separate reconcile directories.
- Avoid destructive commands in source fragments.
- Never use `git reset --hard` or `git checkout --` unless the user explicitly
  requests it.
- Do not infer deletion from absence in a fragment.
- Keep generated/private artifacts out of Git.
- Show real command outputs for key evidence.
- Verify before claiming success.
- Push only after the diff has been summarized.

This workflow is worth keeping because it prevents the exact failure mode that
created the May 2026 drift: useful local work existed, but it had no `.git`
history and no remote backup.
