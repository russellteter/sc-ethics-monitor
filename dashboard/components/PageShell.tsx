"use client";
import { useEffect, useState } from "react";
import { Candidate, FinanceArtifact } from "@/lib/types";
import StatsStrip from "./StatsStrip";
import FinanceTable from "./FinanceTable";
import DistrictGeoMap from "./DistrictGeoMap";
import CandidateDrawer from "./CandidateDrawer";
import KeyboardHelp from "./KeyboardHelp";

interface Props {
  artifact: FinanceArtifact;
}

export default function PageShell({ artifact }: Props) {
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      const isEditable =
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        target?.isContentEditable;
      if (isEditable) return;
      if (e.key === "/") {
        e.preventDefault();
        document
          .querySelector<HTMLInputElement>(
            "input[aria-label='Search candidates']",
          )
          ?.focus();
      } else if (e.key === "?") {
        e.preventDefault();
        setHelpOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <main className="max-w-page mx-auto px-6 lg:px-8 py-6">
      <StatsStrip stats={artifact.stats} />
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <FinanceTable candidates={artifact.candidates} onSelect={setSelected} />
        <div className="hidden lg:block">
          <DistrictGeoMap
            candidates={artifact.candidates}
            onSelect={setSelected}
            selectedId={selected?.id ?? null}
          />
        </div>
      </div>
      <CandidateDrawer candidate={selected} onClose={() => setSelected(null)} />
      <KeyboardHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
    </main>
  );
}
