import "server-only";
import type { FinanceArtifact } from "./types";

const RAW_URL =
  process.env.HOUSE_FINANCE_DATA_URL ||
  "https://raw.githubusercontent.com/russellteter/sc-ethics-monitor/main/data/house_finance.json";

const FIXTURE_URL = process.env.HOUSE_FINANCE_FIXTURE_URL;

export async function fetchHouseFinance(): Promise<FinanceArtifact> {
  const url = FIXTURE_URL || RAW_URL;
  const res = await fetch(url, {
    next: { revalidate: 60, tags: ["house-finance"] },
    headers: { "User-Agent": "sc-house-finance-dashboard/0.1" },
  });
  if (!res.ok) {
    throw new Error(
      `Failed to fetch house_finance.json: ${res.status} ${res.statusText}`,
    );
  }
  const data = (await res.json()) as FinanceArtifact;
  if (data.schema_version !== 1) {
    throw new Error(`Unsupported schema_version: ${data.schema_version}`);
  }
  return data;
}
