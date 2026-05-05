import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const realFetch = global.fetch;

async function loadModule() {
  vi.resetModules();
  return await import("@/lib/data");
}

describe("fetchHouseFinance", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    delete process.env.HOUSE_FINANCE_FIXTURE_URL;
    delete process.env.GH_PAT;
    delete process.env.HOUSE_FINANCE_DATA_URL;
  });

  afterEach(() => {
    global.fetch = realFetch;
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("warns when artifact is older than 8 days", async () => {
    const stale = {
      schema_version: 1,
      generated_at: "2025-01-01T00:00:00Z",
      cycle: "2026",
      candidates: [],
      stats: {},
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => stale,
    } as Response) as unknown as typeof fetch;
    vi.setSystemTime(new Date("2026-05-04T00:00:00Z"));
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { fetchHouseFinance } = await loadModule();
    await fetchHouseFinance();
    expect(warn).toHaveBeenCalledWith(expect.stringMatching(/stale/i));
  });

  it("does not warn when artifact is fresh", async () => {
    const fresh = {
      schema_version: 1,
      generated_at: "2026-05-04T00:00:00Z",
      cycle: "2026",
      candidates: [],
      stats: {},
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => fresh,
    } as Response) as unknown as typeof fetch;
    vi.setSystemTime(new Date("2026-05-05T00:00:00Z"));
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { fetchHouseFinance } = await loadModule();
    await fetchHouseFinance();
    expect(warn).not.toHaveBeenCalled();
  });

  it("throws when raw URL fetch fails (no fixture/PAT)", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    } as Response) as unknown as typeof fetch;
    const { fetchHouseFinance } = await loadModule();
    await expect(fetchHouseFinance()).rejects.toThrow(/404/);
  });
});
