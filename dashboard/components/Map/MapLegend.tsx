// Democrat blue COH tier palette
const TIERS: [string, string][] = [
  ["$0", "#f1f5f9"],
  ["<$10K", "#bfdbfe"],
  ["$10–50K", "#60a5fa"],
  ["$50–100K", "#2563eb"],
  ["$100K+", "#1e3a8a"],
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
