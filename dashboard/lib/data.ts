import "server-only";
import type { FinanceArtifact } from "./types";

const RAW_URL =
  process.env.HOUSE_FINANCE_DATA_URL ||
  "https://raw.githubusercontent.com/russellteter/sc-ethics-monitor/main/data/house_finance.json";

const FIXTURE_URL = process.env.HOUSE_FINANCE_FIXTURE_URL;

const GH_OWNER = process.env.GH_OWNER || "russellteter";
const GH_REPO = process.env.GH_REPO || "sc-ethics-monitor";
const GH_PAT = process.env.GH_PAT;
const GH_DATA_PATH = process.env.GH_DATA_PATH || "data/house_finance.json";
const GH_REF = process.env.GH_REF || "main";

const REVALIDATE_SEC = 60;

interface ContentsApiResponse {
  content: string;
  encoding: "base64" | "none";
}

async function fetchViaGitHubApi(): Promise<FinanceArtifact> {
  const url = `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/contents/${GH_DATA_PATH}?ref=${GH_REF}`;
  const res = await fetch(url, {
    next: { revalidate: REVALIDATE_SEC, tags: ["house-finance"] },
    headers: {
      Authorization: `token ${GH_PAT}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "sc-house-finance-dashboard/0.1",
    },
  });
  if (!res.ok) {
    throw new Error(`GitHub Contents API ${res.status}: ${res.statusText}`);
  }
  const body = (await res.json()) as ContentsApiResponse;
  const decoded =
    body.encoding === "base64"
      ? Buffer.from(body.content, "base64").toString("utf-8")
      : body.content;
  return JSON.parse(decoded) as FinanceArtifact;
}

async function fetchViaUrl(url: string): Promise<FinanceArtifact> {
  const res = await fetch(url, {
    next: { revalidate: REVALIDATE_SEC, tags: ["house-finance"] },
    headers: { "User-Agent": "sc-house-finance-dashboard/0.1" },
  });
  if (!res.ok) {
    throw new Error(
      `Failed to fetch house_finance.json: ${res.status} ${res.statusText}`,
    );
  }
  return (await res.json()) as FinanceArtifact;
}

export async function fetchHouseFinance(): Promise<FinanceArtifact> {
  let data: FinanceArtifact;
  if (FIXTURE_URL) {
    data = await fetchViaUrl(FIXTURE_URL);
  } else if (GH_PAT) {
    data = await fetchViaGitHubApi();
  } else {
    data = await fetchViaUrl(RAW_URL);
  }
  if (data.schema_version !== 1) {
    throw new Error(`Unsupported schema_version: ${data.schema_version}`);
  }
  if (data.generated_at) {
    const ageMs = Date.now() - new Date(data.generated_at).getTime();
    const days = ageMs / (1000 * 60 * 60 * 24);
    if (days > 8) {
      console.warn(
        `[house-finance] artifact is stale: ${days.toFixed(1)} days old (generated_at=${data.generated_at}); cron may be failing`,
      );
    }
  }
  return data;
}
