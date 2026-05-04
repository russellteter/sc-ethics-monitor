"use client";
import { Candidate } from "@/lib/types";
import { cohTier, cohTierColor } from "@/lib/cohTier";
import { DISTRICT_POSITIONS } from "@/lib/districts";
import { useMemo, useState } from "react";
import Legend from "./Legend";

interface Props {
  candidates: Candidate[];
  onSelect: (c: Candidate) => void;
}

export default function DistrictMap({ candidates, onSelect }: Props) {
  const byDistrict = useMemo(() => {
    const m = new Map<number, Candidate>();
    for (const c of candidates) m.set(c.district, c);
    return m;
  }, [candidates]);
  const [hovered, setHovered] = useState<number | null>(null);
  const hoverCand = hovered !== null ? (byDistrict.get(hovered) ?? null) : null;

  return (
    <div className="bg-card border border-line rounded-lg shadow-card">
      <div className="px-4 py-3 border-b border-line">
        <h3 className="font-display font-bold text-sm">District Map</h3>
        <p className="text-[11px] text-muted mt-0.5">
          124 SC House districts · color = cash on hand
        </p>
      </div>
      <div className="p-4 relative">
        <svg
          viewBox="0 0 240 280"
          className="w-full h-auto"
          role="img"
          aria-label="SC House district cartogram"
        >
          {DISTRICT_POSITIONS.map((p) => {
            const cand = byDistrict.get(p.district);
            const t = cohTier(cand?.latest_report?.cash_on_hand ?? null);
            const isHovered = hovered === p.district;
            return (
              <g key={p.district}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isHovered ? 8 : 6}
                  fill={cohTierColor(t)}
                  stroke={isHovered ? "#1A4A45" : "#E5E7EB"}
                  strokeWidth={isHovered ? 1.5 : 0.5}
                  onMouseEnter={() => setHovered(p.district)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => cand && onSelect(cand)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && cand) onSelect(cand);
                  }}
                  tabIndex={cand ? 0 : -1}
                  className="cursor-pointer focus:outline-none"
                />
              </g>
            );
          })}
        </svg>
        {hoverCand && hoverCand.latest_report && (
          <div className="absolute top-2 right-2 bg-ink text-white text-[11px] px-3 py-2 rounded-md shadow-lg max-w-[200px] pointer-events-none">
            <div className="font-semibold">
              D-{hoverCand.district} · {hoverCand.name}
            </div>
            <div className="opacity-80 mt-0.5">
              ${Math.round(hoverCand.latest_report.cash_on_hand).toLocaleString()} COH
            </div>
          </div>
        )}
      </div>
      <Legend />
    </div>
  );
}
