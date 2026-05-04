import { describe, expect, it } from "vitest";
import { tryAcquire } from "@/lib/rateLimit";

describe("tryAcquire", () => {
  it("allows the first request", () => {
    const store = new Map<string, number>();
    expect(tryAcquire(store, "1.2.3.4", { intervalMs: 60_000, now: 1000 })).toBe(
      true,
    );
  });
  it("blocks within interval", () => {
    const store = new Map<string, number>();
    tryAcquire(store, "1.2.3.4", { intervalMs: 60_000, now: 1000 });
    expect(tryAcquire(store, "1.2.3.4", { intervalMs: 60_000, now: 5000 })).toBe(
      false,
    );
  });
  it("re-allows after interval", () => {
    const store = new Map<string, number>();
    tryAcquire(store, "1.2.3.4", { intervalMs: 60_000, now: 1000 });
    expect(
      tryAcquire(store, "1.2.3.4", { intervalMs: 60_000, now: 65_000 }),
    ).toBe(true);
  });
});
