import { describe, expect, it } from "vitest";
import { toCsv } from "@/lib/csv";

describe("toCsv", () => {
  it("emits header and rows", () => {
    const rows = [
      { name: "Heather Bauer", coh: 68449 },
      { name: "Roger Kirby, Esq.", coh: 0 },
    ];
    const csv = toCsv(rows, [
      { key: "name", label: "Candidate" },
      { key: "coh", label: "Cash on Hand" },
    ]);
    expect(csv.split("\n")[0]).toBe("Candidate,Cash on Hand");
    expect(csv).toContain('"Roger Kirby, Esq."');
  });

  it("escapes quotes by doubling", () => {
    const csv = toCsv([{ note: 'He said "hi"' }], [{ key: "note", label: "Note" }]);
    expect(csv).toContain('"He said ""hi"""');
  });

  it("handles null/undefined as empty", () => {
    const csv = toCsv(
      [{ x: null, y: undefined }],
      [
        { key: "x", label: "X" },
        { key: "y", label: "Y" },
      ],
    );
    expect(csv.split("\n")[1]).toBe(",");
  });

  it("escapes newlines inside cells", () => {
    const csv = toCsv(
      [{ note: "line1\nline2" }],
      [{ key: "note", label: "Note" }],
    );
    expect(csv).toContain('"line1\nline2"');
  });

  it("emits header-only CSV for empty rows", () => {
    const csv = toCsv([] as Array<{ a: string }>, [{ key: "a", label: "A" }]);
    expect(csv).toBe("A\n");
  });
});
