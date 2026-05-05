import { Stats } from "@/lib/types";
import { formatCurrencyShort } from "@/lib/format";
import KPICard from "./KPICard";

interface Props {
  stats: Stats;
}

export default function StatsStrip({ stats }: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
      <KPICard
        label="Tracked"
        value={String(stats.total_dem_house)}
        sub="Dem House candidates"
      />
      <KPICard
        label="Filed"
        value={String(stats.filed)}
        sub="Q1 reports submitted"
      />
      <KPICard
        label="Not filed"
        value={String(stats.not_filed)}
        sub="missing Q1 disclosure"
        valueColor="text-red-600"
      />
      <KPICard
        label="Median COH"
        value={formatCurrencyShort(stats.median_coh)}
        sub="cash on hand"
        accent
      />
      <KPICard
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
