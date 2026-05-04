"use client";
import { Candidate } from "@/lib/types";
import { downloadCsv, toCsv } from "@/lib/csv";

interface Props {
  candidates: Candidate[];
}

export default function ExportButton({ candidates }: Props) {
  function onClick() {
    const rows = candidates.map((c) => ({
      name: c.name,
      district: c.district,
      filing_status: c.filing_status,
      period_raised: c.latest_report?.period_raised ?? "",
      total_raised: c.latest_report?.total_raised ?? "",
      cash_on_hand: c.latest_report?.cash_on_hand ?? "",
      filed_date: c.latest_report?.filed_date ?? "",
      url: c.latest_report?.url ?? "",
    }));
    const csv = toCsv(rows, [
      { key: "name", label: "Candidate" },
      { key: "district", label: "District" },
      { key: "filing_status", label: "Status" },
      { key: "period_raised", label: "Period Raised" },
      { key: "total_raised", label: "Total Raised" },
      { key: "cash_on_hand", label: "Cash on Hand" },
      { key: "filed_date", label: "Filed Date" },
      { key: "url", label: "Ethics Report URL" },
    ]);
    const stamp = new Date().toISOString().slice(0, 10);
    downloadCsv(`sc-house-finance-${stamp}.csv`, csv);
  }

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Export current view as CSV"
      className="text-xs px-3 py-1.5 border border-line rounded-md hover:border-teal-primary hover:text-teal-deep focus:outline-none focus:ring-2 focus:ring-teal-primary/40 transition-colors"
    >
      Export CSV
    </button>
  );
}
