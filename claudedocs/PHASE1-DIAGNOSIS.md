# Phase 1 Diagnosis — Deployed Data Fetch

**Date:** 2026-05-04 (EDT) / 2026-05-05 (UTC)
**Owner:** FE-Foundation
**Plan:** `~/.claude/plans/read-tasks-handoff-md-and-continue-snug-lampson.md`

## Summary

**Data flow is healthy.** The aliased prod URL renders all 162 Dem House candidates with the correct filed/not-filed split (53/108/1). The user's "1 candidate visible" report appears to predate commit `c9a1a80` (which unblocked 53 finance reports) or was a transient screenshot.

**However, the build pipeline is broken.** 16 of the last 17 git-triggered prod deploys errored. The current Ready alias is held in place by a single CLI-uploaded build from 3h ago. The next dashboard code push will not reach users.

## Findings

### Artifact (`main`)
| Field | Value |
|---|---|
| `candidates` | 162 |
| `stats.filed` | 53 |
| `stats.not_filed` | 108 |
| `stats.scrape_failed` | 1 |
| `generated_at` | `2026-05-05T02:48:39+00:00` (~1h ago) |

`raw.githubusercontent.com/.../main/data/house_finance.json` returns the same.

### Vercel envs (production)
| Var | Status |
|---|---|
| `HOUSE_FINANCE_DATA_URL` | Set (Encrypted, 9h ago, both Production + Preview) |
| `GH_PAT` | Set (Encrypted, 9h ago, both Production + Preview) |
| `HOUSE_FINANCE_FIXTURE_URL` | Not set (correct) |
| `GH_OWNER` / `GH_REPO` / `GH_REF` | Not set; defaults work |

`fetchHouseFinance()` flow with these envs: `FIXTURE_URL` unset → `GH_PAT` set → would call `fetchViaGitHubApi()`. **Note:** `HOUSE_FINANCE_DATA_URL` is set but never consumed when `GH_PAT` is also present (current `data.ts` precedence: fixture → API → raw URL). Either is fine; data renders correctly.

### Production rendering (`https://sc-house-finance.vercel.app`)
| Probe | Count |
|---|---|
| `<tr ` rows | 163 (1 header + 162 candidates) |
| Unique `D-N` district refs | 124 (full map) |
| Emerald "filed" badges | 53 |
| Red "not filed" badges | 108 |
| Amber "scrape error" badges | 1 |

Distribution matches the artifact exactly. All 162 candidates render. **No 1-candidate truncation observed.**

### Deploy status — 16 errors in a row
Last successful production deploy: `dpl_9xX4DdKFkRr7E4LsqTpzRTtMQswv` at 2026-05-04 21:00 EDT (CLI-uploaded, "Downloading 61 deployment files...").

Every git-triggered prod deploy after that errored with:
```
Error: > Couldn't find any `pages` or `app` directory. Please create one under the project root
  at findPagesDir (/vercel/path0/node_modules/next/dist/lib/find-pages-dir.js:42:15)
```

The build process clones `russellteter/sc-ethics-monitor` to `/vercel/path0`, then `next build` looks for `app/` or `pages/` at that path. Repo root has no `app/` — it's at `dashboard/app/`. Two pieces of evidence:
- Successful build was CLI-uploaded with `cd dashboard && npx vercel`, so files arrived at `/vercel/path0` *as* the dashboard tree.
- Failed builds (e.g. `ovi3m9t6b` at 22:53 EDT, on commit `c9a1a80`) clone the full repo and produce `/vercel/path0/dashboard/app/...` but `next build` runs at `/vercel/path0`.

## Root causes

1. **Vercel project Root Directory unset.** Should be `dashboard`. Without it, every git-triggered deploy fails. This is a project-settings change (Vercel dashboard or `vercel project` reconfig), not an env-var change.
2. **Aliased prod URL is frozen** on the 21:00 EDT CLI deploy. Looks healthy now because ISR (`revalidate: 60s`) re-fetches the artifact per request from raw.githubusercontent.com. The moment the next dashboard code change pushes, the alias stays put (no successful build to promote) and stale code persists indefinitely.
3. **Sunday cron will not move the alias either** — the cron only commits `data/house_finance.json`; it doesn't ship UI code. ISR catches data changes regardless. But any future UI commit (Phases 2–7) will silently fail to reach users until Root Directory is fixed.

## Recommended action (out of scope for Task 1.1)

For Deploy (Task #3 / Phase 1.3):
- Set Vercel project Root Directory to `dashboard` via Vercel dashboard or `vercel link`/`vercel project` reconfig.
- After fix, push a no-op dashboard commit and confirm the next git-triggered prod deploy reaches Ready.
- Document in `claudedocs/RUNBOOK.md`.

For FE-Foundation (Task #2 / Phase 1.2):
- Add staleness warning to `data.ts` per plan (this is independent of the build issue).
