import { describe, expect, it } from "vitest";
import { formatCurrency, formatCurrencyShort, formatDate, formatDistrict } from "@/lib/format";

describe("formatCurrency", () => {
  it("formats whole dollars", () => {
    expect(formatCurrency(68448.57)).toBe("$68,449");
  });
  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });
  it("returns em dash for null", () => {
    expect(formatCurrency(null)).toBe("—");
  });
});

describe("formatCurrencyShort", () => {
  it("formats thousands", () => {
    expect(formatCurrencyShort(24500)).toBe("$24.5K");
  });
  it("formats millions", () => {
    expect(formatCurrencyShort(1420000)).toBe("$1.4M");
  });
  it("formats sub-thousand", () => {
    expect(formatCurrencyShort(842)).toBe("$842");
  });
});

describe("formatDate", () => {
  it("formats YYYY-MM-DD as Mon D", () => {
    expect(formatDate("2026-04-10")).toBe("Apr 10");
  });
});

describe("formatDistrict", () => {
  it("prefixes D-", () => {
    expect(formatDistrict(75)).toBe("D-75");
  });
});
