"use client";
import { useState } from "react";
import { Candidate, FinanceArtifact } from "@/lib/types";
import StatsStrip from "./StatsStrip";
import FinanceTable from "./FinanceTable";
import DistrictMap from "./DistrictMap";
import CandidateDrawer from "./CandidateDrawer";

interface Props {
  artifact: FinanceArtifact;
}

export default function PageShell({ artifact }: Props) {
  const [selected, setSelected] = useState<Candidate | null>(null);
  return (
    <main className="max-w-page mx-auto px-6 lg:px-8 py-6">
      <StatsStrip stats={artifact.stats} />
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <FinanceTable candidates={artifact.candidates} onSelect={setSelected} />
        <DistrictMap candidates={artifact.candidates} onSelect={setSelected} />
      </div>
      <CandidateDrawer candidate={selected} onClose={() => setSelected(null)} />
    </main>
  );
}
