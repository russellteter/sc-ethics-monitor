# SC House Dem Finance Dashboard

Next.js 14 (App Router, TypeScript, Tailwind) dashboard rendering the
`data/house_finance.json` artifact published by the finance scraper.

## Local development

```bash
npm install
npm run dev
```

The page fetches from `process.env.HOUSE_FINANCE_DATA_URL` (defaults to the
GitHub raw URL on `main`). To run against the bundled fixture:

```bash
npx --yes serve -l 4173 e2e/fixtures &
HOUSE_FINANCE_DATA_URL=http://localhost:4173/house_finance.json npm run dev
```

## Tests

```bash
npm test         # vitest — format / cohTier / rateLimit (19 tests)
npm run build    # Next production build
```

## Refresh API (`POST /api/refresh`)

Triggers a `workflow_dispatch` against `refresh-finance.yml` in the
`russellteter/sc-ethics-monitor` repo. Required env vars:

- `GH_PAT` — GitHub Personal Access Token with `actions:write`. **Without
  it, the route returns 500.** This is expected in dev when the secret
  isn't configured.
- `GH_OWNER` (optional, default `russellteter`)
- `GH_REPO` (optional, default `sc-ethics-monitor`)
- `GH_WORKFLOW` (optional, default `refresh-finance.yml`)
- `CRON_SHARED_SECRET` (optional) — if set, requests with
  `?token=<secret>` bypass the per-IP rate limit.

Anonymous browser requests are rate-limited to one POST per 60 seconds
per IP via `lib/rateLimit.ts`.

## Data flow

```
data/house_finance.json (Backend agent writes)
        |
        v fetched server-side, ISR 60s
   app/page.tsx -> Header + PageShell (StatsStrip, FinanceTable,
                                       DistrictMap, CandidateDrawer)
```

The TypeScript types in `lib/types.ts` mirror the artifact schema
(`schema_version: 1`) defined in the project plan.
