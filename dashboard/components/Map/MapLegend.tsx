const TIERS: [string, string][] = [
  ["$0", "var(--slate-100)"],
  ["<$10K", "var(--brand-200)"],
  ["$10–50K", "var(--brand-400)"],
  ["$50–100K", "var(--brand-600)"],
  ["$100K+", "var(--brand-800)"],
];

export default function MapLegend() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-t border-slate-200 text-[11px] text-slate-500 flex-wrap">
      <span>COH tier:</span>
      {TIERS.map(([label, color]) => (
        <span key={label} className="flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded-sm border border-slate-200"
            style={{ background: color }}
            aria-hidden
          />
          {label}
        </span>
      ))}
    </div>
  );
}
