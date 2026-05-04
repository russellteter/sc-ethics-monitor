export interface Column<T> {
  key: keyof T;
  label: string;
}

function escape(v: unknown): string {
  if (v === null || v === undefined) return "";
  const s = String(v);
  if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

export function toCsv<T extends Record<string, unknown>>(
  rows: T[],
  cols: Column<T>[],
): string {
  const header = cols.map((c) => c.label).join(",");
  if (rows.length === 0) return header + "\n";
  const body = rows
    .map((r) => cols.map((c) => escape(r[c.key])).join(","))
    .join("\n");
  return header + "\n" + body;
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
