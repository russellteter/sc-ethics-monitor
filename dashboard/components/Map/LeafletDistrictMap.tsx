"use client";
import dynamic from "next/dynamic";
import type { Candidate } from "@/lib/types";

const InnerMap = dynamic(() => import("./InnerLeafletMap"), {
  ssr: false,
  loading: () => (
    <div
      className="glass-card h-[560px] animate-pulse bg-slate-100 rounded-xl"
      aria-label="Loading district map"
    />
  ),
});

interface Props {
  candidates: Candidate[];
  onSelect: (c: Candidate) => void;
  selectedId: string | null;
}

export default function LeafletDistrictMap(p: Props) {
  return <InnerMap {...p} />;
}
