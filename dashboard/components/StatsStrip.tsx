import { Stats } from "@/lib/types";
import { formatCurrencyShort } from "@/lib/format";

interface Props {
  stats: Stats;
}

export default function StatsStrip({ stats }: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
      <Card
        label="Tracked"
        value={String(stats.total_dem_house)}
        sub="Dem House candidates"
      />
      <Card
        label="Filed"
        value={String(stats.filed)}
        sub="Q1 reports submitted"
      />
      <Card
        label="Not filed"
        value={String(stats.not_filed)}
        sub="missing Q1 disclosure"
        valueColor="text-red-600"
      />
      <Card
        label="Median COH"
        value={formatCurrencyShort(stats.median_coh)}
        sub="cash on hand"
        accent
      />
      <Card
        label="Top COH"
        value={formatCurrencyShort(stats.top_coh)}
        sub={
          stats.top_coh_candidate
            ? `${stats.top_coh_candidate} · D-${stats.top_coh_district}`
            : ""
        }
        accent
      />
    </div>
  );
}

function Card({
  label,
  value,
  sub,
  valueColor,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  valueColor?: string;
  accent?: boolean;
}) {
  // Teal is reserved as the COH visual anchor; everything else uses slate.
  const valueClass = valueColor ?? (accent ? "text-teal-deep" : "text-slate-900");
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">
        {label}
      </div>
      <div
        className={`font-display text-[28px] leading-none font-bold tabular ${valueClass}`}
      >
        {value}
      </div>
      {sub && <div className="text-[11px] text-slate-500 mt-1.5">{sub}</div>}
    </div>
  );
}
