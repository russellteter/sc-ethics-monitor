# Report-detail HTML structure (verified 2026-05-04 against Heather Bauer Q1 2026)

The Ethics report-detail page is an Angular SPA. Static HTML fetch returns ~2KB shell;
real content requires JS rendering (Playwright). After render, the financial summary is
a table with **3-column rows**: `Label | This Period | Aggregate`.

## Actual data structure for `heather_bauer_418208.html`

```
RECEIPTS SECTION:
  Cash Contributions       | $32,801.00 | $89,366.10
  In-kind Contributions    | $0.00      | $0.00
  Debt Setoff Funds        | $0.00      | $0.00
  Personal Contributions   | $0.00      | $0.00
  Loans                    | $0.00      | $0.00
  Account Credits          | $5.90      | $6.01
  Total                    | $32,806.90 | $89,372.11   ← receipts total

EXPENDITURES SECTION:
  Expenditures             | $8,041.87  | $19,054.11
  Returned Contributions   | $0.00      | $0.00
  In-Kind Expenditures     | $0.00      | $0.00
  Total                    | $8,041.87  | $19,054.11   ← expenditures total

BALANCE SECTION:
  Campaign Funds           | $43,683.54 | $68,448.57   ← cash on hand
  Loans                    | $0.00      | $0.00
```

## Three target numbers and their source

| Field | Row label | Column |
|---|---|---|
| `period_raised` | "Total" (in receipts section) | This Period (col 1 of values) |
| `total_raised` | "Total" (in receipts section) | Aggregate (col 2 of values) |
| `cash_on_hand` | "Campaign Funds" | Aggregate (col 2 of values) |

## Important nuances

- "Total" appears **twice** (after Receipts, after Expenditures). Parser MUST anchor
  by section, not just match "Total". Strategy: find first `Total` row that sits
  between rows containing "Cash Contributions" and "Expenditures".
- The traditional label "Cash on Hand" / "Ending Cash Balance" does NOT appear. The
  SC Ethics terminology is "Campaign Funds".
- Numbers are formatted with `$` and thousands commas: `$32,806.90`.

## Source
User-provided example (https://ethicsfiling.sc.gov/.../report-detail?reportId=418208)
listed numbers as 32806.90 / 89,371.11 / 68,448.57. Live page actually shows
89,372.11 (off by $1.00 — likely amendment or rounding in source). Period raised and
COH match exactly.
