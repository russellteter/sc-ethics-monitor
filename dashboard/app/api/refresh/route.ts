import { NextRequest, NextResponse } from "next/server";
import { tryAcquire } from "@/lib/rateLimit";

const RATE_STORE = new Map<string, number>();
const RATE_INTERVAL = 60_000;

export async function POST(req: NextRequest) {
  const isCron = req.headers.get("x-vercel-cron") === "1";
  const cronToken = req.nextUrl.searchParams.get("token");
  if (cronToken && cronToken === process.env.CRON_SHARED_SECRET) {
    return triggerWorkflow("cron-token");
  }
  if (isCron) {
    return triggerWorkflow("vercel-cron");
  }
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0] ?? "anon";
  if (!tryAcquire(RATE_STORE, ip, { intervalMs: RATE_INTERVAL })) {
    return NextResponse.json(
      { ok: false, error: "rate-limited" },
      { status: 429 },
    );
  }
  return triggerWorkflow(`ip:${ip}`);
}

async function triggerWorkflow(reason: string) {
  const pat = process.env.GH_PAT;
  if (!pat)
    return NextResponse.json(
      { ok: false, error: "missing GH_PAT" },
      { status: 500 },
    );
  const owner = process.env.GH_OWNER || "russellteter";
  const repo = process.env.GH_REPO || "sc-ethics-monitor";
  const workflow = process.env.GH_WORKFLOW || "refresh-finance.yml";
  const r = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `token ${pat}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main", inputs: { reason } }),
    },
  );
  if (!r.ok) {
    const text = await r.text();
    return NextResponse.json(
      { ok: false, error: text.slice(0, 200) },
      { status: r.status },
    );
  }
  return NextResponse.json({ ok: true, reason }, { status: 202 });
}
