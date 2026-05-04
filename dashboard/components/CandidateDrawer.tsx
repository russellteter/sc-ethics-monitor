"use client";
import { Candidate } from "@/lib/types";
import { formatCurrency, formatDate, formatDistrict } from "@/lib/format";
import { useEffect, useRef } from "react";

interface Props {
  candidate: Candidate | null;
  onClose: () => void;
}

export default function CandidateDrawer({ candidate, onClose }: Props) {
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!candidate) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [candidate, onClose]);

  useEffect(() => {
    if (candidate) {
      // Capture the element that opened the drawer so we can return focus on close.
      triggerRef.current = document.activeElement as HTMLElement | null;
      // Defer focus to next tick so the drawer is mounted and focusable.
      const id = window.setTimeout(() => closeBtnRef.current?.focus(), 0);
      return () => window.clearTimeout(id);
    }
    // Drawer closed: return focus to the originating row.
    triggerRef.current?.focus?.();
  }, [candidate]);

  if (!candidate) return null;
  const r = candidate.latest_report;
  return (
    <>
      <div
        className="fixed inset-0 bg-slate-900/30 z-40"
        onClick={onClose}
        aria-hidden
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`${candidate.name} details`}
        className="fixed top-0 right-0 h-full w-full sm:w-[420px] bg-white border-l border-slate-200 shadow-xl z-50 overflow-y-auto"
      >
        <div className="p-5 border-b border-slate-200 flex items-start justify-between bg-slate-50">
          <div>
            <h2 className="font-display font-semibold text-2xl text-slate-900 tracking-tight">
              {candidate.name}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {formatDistrict(candidate.district)} · {candidate.party}
            </p>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onClose}
            aria-label="Close candidate details"
            className="text-slate-500 hover:text-slate-900 text-xl leading-none px-2 focus:outline-none focus:ring-2 focus:ring-teal-primary/40 rounded"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
        {r ? (
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Period raised" value={formatCurrency(r.period_raised)} />
              <Stat label="Total raised" value={formatCurrency(r.total_raised)} />
              <Stat
                label="Cash on hand"
                value={formatCurrency(r.cash_on_hand)}
                highlight
              />
            </div>
            <div className="text-sm">
              <div className="text-slate-500 text-[11px] uppercase tracking-wide mb-1">
                Latest report
              </div>
              <div className="space-y-1">
                <div className="text-slate-900">
                  {r.report_type} · {r.period_label}
                  {r.is_amended && " (amended)"}
                </div>
                <div className="text-slate-500">Filed {formatDate(r.filed_date)}</div>
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-teal-deep underline underline-offset-2 mt-1 hover:text-teal-mid"
                >
                  View on ethicsfiling.sc.gov →
                </a>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-5 text-sm text-slate-500">
            No quarterly disclosure on file yet.
            {candidate.last_error && (
              <div className="mt-3 text-xs text-amber-700">
                Last scrape error: {candidate.last_error}
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  // Teal accent reserved for COH (highlight); other stats use slate.
  const cls = highlight
    ? "p-3 rounded-lg border border-teal-primary bg-teal-primary/5"
    : "p-3 rounded-lg border border-slate-200 bg-slate-50";
  return (
    <div className={cls}>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div
        className={`font-display font-bold mt-1 text-base tabular ${
          highlight ? "text-teal-deep" : "text-slate-900"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
