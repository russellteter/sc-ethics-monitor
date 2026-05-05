import { formatDate } from "@/lib/format";
import ChamberToggle from "./ChamberToggle";
import DataFreshnessBanner from "./DataFreshnessBanner";

interface Props {
  generatedAt: string | null;
  cycle: string;
}

export default function Header({ generatedAt, cycle }: Props) {
  return (
    <header className="sticky top-0 z-30 bg-card border-b border-line px-8 py-4 flex items-center justify-between gap-4 flex-wrap">
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-lg"
          style={{ background: "linear-gradient(135deg, #1ED4C2, #1A4A45)" }}
          aria-hidden
        />
        <div>
          <h1 className="font-display text-xl font-semibold tracking-tight text-slate-900">
            SC House Dem Finance
          </h1>
          <p className="text-xs text-muted">Locality AI · Q1 {cycle}</p>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted">
        <ChamberToggle active="house" />
        <DataFreshnessBanner generatedAt={generatedAt} />
      </div>
    </header>
  );
}
