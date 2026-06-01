# Vercel PR previews (designer console UI)

Vercel deploys the **SvelteKit frontend only** (`webapp/frontend`). Each pull request gets a
preview URL in a GitHub comment after the Vercel GitHub app is connected.

The FastAPI pipeline (`webapp/backend`) does **not** run on Vercel. Previews show the console
UI and copy; staged runs still need local `arch-lw-web-console` or a future hosted API.

Posting/public proof remains **NO-GO** on previews — same as local.

## One-time setup (you)

1. Sign in at [vercel.com](https://vercel.com) (same account as `vercel whoami`).
2. Install the GitHub app: [github.com/apps/vercel](https://github.com/apps/vercel) → grant access to `zohartito/arch-line-weights`.
3. In Vercel → **Add New Project** → import `zohartito/arch-line-weights`.
4. Set **Root Directory** to `webapp/frontend` (required).
5. Framework should detect **SvelteKit**; build uses `vercel.json` in that folder.
6. Deploy **Production** from `main` (optional). Enable **Preview** deployments for all branches / PRs.

Or from this repo (after the config below is on your branch):

```bash
cd webapp/frontend
vercel link          # link to team/project
vercel git connect   # wire GitHub → previews on PRs
```

## What you get on each PR

- A **Vercel bot comment** with a preview link (e.g. `arch-line-weights-….vercel.app`).
- UI changes in `webapp/frontend/` are reviewable in the browser without a local `npm run dev`.

## Limits (honest)

| Works on preview | Does not |
|------------------|----------|
| Layout, copy, console screens, static navigation | `arch-lw` CLI on server |
| Build/check CI parity with `npm run build` | Upload + apply + poché (needs local API) |
| NO-GO / W5/W7 labels in the UI | Real proof packets or private USC files |

## Optional env (Vercel project settings)

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Only if you later host the FastAPI backend; leave unset for UI-only previews |

## Troubleshooting

- **Build fails:** run `cd webapp/frontend && npm ci && npm run build` locally.
- **No PR comment:** confirm the Vercel app is installed on the repo and previews are enabled for the PR branch.
- **Wrong directory:** Root Directory must be `webapp/frontend`, not the repo root.
