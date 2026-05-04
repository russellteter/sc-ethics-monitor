"use client";
import { useMemo, useState } from "react";
import { Candidate, FilterMode, SortDir, SortKey } from "@/lib/types";
import { formatCurrency, formatDate, formatDistrict } from "@/lib/format";
import SearchInput from "./SearchInput";
import FilterPills from "./FilterPills";
import ExportButton from "./ExportButton";
import EmptyState from "./EmptyState";

interface Props {
  candidates: Candidate[];
  onSelect: (c: Candidate) => void;
}

export default function FinanceTable({ candidates, onSelect }: Props) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterMode>("all");
  const [sortKey, setSortKey] = useState<SortKey>("cash_on_hand");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const districtCounts = useMemo(() => {
    const m = new Map<number, number>();
    for (const c of candidates) m.set(c.district, (m.get(c.district) ?? 0) + 1);
    return m;
  }, [candidates]);

  const rows = useMemo(() => {
    const filtered = candidates.filter((c) => {
      if (
        search &&
        !`${c.name} ${formatDistrict(c.district)}`
          .toLowerCase()
          .includes(search.toLowerCase())
      )
        return false;
      if (filter === "filed" && c.filing_status !== "filed") return false;
      if (filter === "not_filed" && c.filing_status !== "not_filed") return false;
      if (
        filter === "coh_50k_plus" &&
        (c.latest_report?.cash_on_hand ?? 0) < 50_000
      )
        return false;
      if (filter === "contested" && (districtCounts.get(c.district) ?? 0) <= 1)
        return false;
      return true;
    });
    return [...filtered].sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [candidates, search, filter, sortKey, sortDir, districtCounts]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(k);
      setSortDir(k === "name" || k === "district" ? "asc" : "desc");
    }
  }

  return (
    <div className="bg-card border border-line rounded-lg shadow-card overflow-hidden">
      <div className="px-4 py-3 border-b border-line flex items-center justify-between gap-4 flex-wrap">
        <h2 className="font-display font-bold text-sm">All Dem House Candidates</h2>
        <div className="flex items-center gap-3">
          <div className="text-xs text-muted tabular">
            {rows.length} of {candidates.length} · Click column header to sort
          </div>
          <ExportButton candidates={rows} />
        </div>
      </div>
      <div className="px-4 py-3 border-b border-line flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
        <div className="md:max-w-sm flex-1">
          <SearchInput value={search} onChange={setSearch} />
        </div>
        <FilterPills value={filter} onChange={setFilter} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="bg-[#FAFAFA] text-[11px] uppercase tracking-wider text-muted">
              <Th onClick={() => toggleSort("name")} active={sortKey === "name"} dir={sortDir}>
                Candidate
              </Th>
              <Th
                onClick={() => toggleSort("district")}
                active={sortKey === "district"}
                dir={sortDir}
              >
                District
              </Th>
              <Th
                align="right"
                onClick={() => toggleSort("period_raised")}
                active={sortKey === "period_raised"}
                dir={sortDir}
              >
                Period raised
              </Th>
              <Th
                align="right"
                onClick={() => toggleSort("total_raised")}
                active={sortKey === "total_raised"}
                dir={sortDir}
              >
                Total raised
              </Th>
              <Th
                align="right"
                onClick={() => toggleSort("cash_on_hand")}
                active={sortKey === "cash_on_hand"}
                dir={sortDir}
              >
                Cash on hand
              </Th>
              <Th
                onClick={() => toggleSort("filed_date")}
                active={sortKey === "filed_date"}
                dir={sortDir}
              >
                Filed
              </Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => {
              const r = c.latest_report;
              const isMissing = !r;
              return (
                <tr
                  key={c.id}
                  tabIndex={0}
                  onClick={() => onSelect(c)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onSelect(c);
                  }}
                  className="border-b border-line last:border-0 hover:bg-[#FAFCFC] cursor-pointer focus:outline-none focus:bg-teal-primary/10"
                >
                  <td className="px-4 py-3">
                    <strong>{c.name}</strong>
                  </td>
                  <td className="px-4 py-3">{formatDistrict(c.district)}</td>
                  <td
                    className={`px-4 py-3 text-right tabular ${
                      isMissing ? "text-muted" : "font-medium"
                    }`}
                  >
                    {formatCurrency(r?.period_raised ?? null)}
                  </td>
                  <td
                    className={`px-4 py-3 text-right tabular ${
                      isMissing ? "text-muted" : "font-medium"
                    }`}
                  >
                    {formatCurrency(r?.total_raised ?? null)}
                  </td>
                  <td
                    className={`px-4 py-3 text-right tabular ${
                      isMissing ? "text-muted" : "font-bold text-teal-deep"
                    }`}
                  >
                    {formatCurrency(r?.cash_on_hand ?? null)}
                  </td>
                  <td className={`px-4 py-3 ${isMissing ? "text-muted" : ""}`}>
                    {formatDate(r?.filed_date ?? null)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.filing_status} />
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7}>
                  <EmptyState
                    title="No matches"
                    sub="Try clearing filters or adjusting the search."
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({
  children,
  onClick,
  active,
  dir,
  align = "left",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  active?: boolean;
  dir?: SortDir;
  align?: "left" | "right";
}) {
  return (
    <th
      onClick={onClick}
      className={`px-4 py-2.5 font-semibold cursor-pointer select-none border-b border-line hover:text-teal-deep ${
        align === "right" ? "text-right" : "text-left"
      } ${active ? "text-teal-deep" : ""}`}
    >
      {children}
      {active && (dir === "asc" ? " ↑" : " ↓")}
    </th>
  );
}

function StatusBadge({ status }: { status: Candidate["filing_status"] }) {
  if (status === "filed")
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-teal-primary/15 text-teal-deep">
        D
      </span>
    );
  if (status === "not_filed")
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-50 text-red-600">
        Not filed
      </span>
    );
  return (
    <span className="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700">
      Scrape failed
    </span>
  );
}

function sortValue(c: Candidate, key: SortKey): number | string {
  switch (key) {
    case "name":
      return c.name.toLowerCase();
    case "district":
      return c.district;
    case "period_raised":
      return c.latest_report?.period_raised ?? -Infinity;
    case "total_raised":
      return c.latest_report?.total_raised ?? -Infinity;
    case "cash_on_hand":
      return c.latest_report?.cash_on_hand ?? -Infinity;
    case "filed_date":
      return c.latest_report?.filed_date ?? "";
  }
}
