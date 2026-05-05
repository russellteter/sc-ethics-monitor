import { describe, expect, it } from "vitest";
import { cohTier, cohTierColor, cohTierLabel } from "@/lib/cohTier";

describe("cohTier", () => {
  it("returns 0 for null", () => expect(cohTier(null)).toBe(0));
  it("returns 0 for $0", () => expect(cohTier(0)).toBe(0));
  it("returns 1 for under 10K", () => expect(cohTier(5000)).toBe(1));
  it("returns 2 for 10–50K", () => expect(cohTier(24500)).toBe(2));
  it("returns 3 for 50–100K", () => expect(cohTier(68449)).toBe(3));
  it("returns 4 for 100K+", () => expect(cohTier(112400)).toBe(4));
});

describe("cohTierColor", () => {
  it("returns a CSS var token for each tier", () => {
    [0, 1, 2, 3, 4].forEach((t) =>
      expect(cohTierColor(t as 0 | 1 | 2 | 3 | 4)).toMatch(/^var\(--/),
    );
  });
  it("uses the slate/indigo brand palette", () => {
    expect(cohTierColor(0)).toBe("var(--slate-100)");
    expect(cohTierColor(1)).toBe("var(--brand-200)");
    expect(cohTierColor(2)).toBe("var(--brand-400)");
    expect(cohTierColor(3)).toBe("var(--brand-600)");
    expect(cohTierColor(4)).toBe("var(--brand-800)");
  });
});

describe("cohTierLabel", () => {
  it("returns a non-empty label for each tier", () => {
    [0, 1, 2, 3, 4].forEach((t) =>
      expect(cohTierLabel(t as 0 | 1 | 2 | 3 | 4).length).toBeGreaterThan(0),
    );
  });
});
