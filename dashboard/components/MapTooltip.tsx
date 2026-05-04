"use client";
import { Candidate } from "@/lib/types";
import { formatCurrency, formatDistrict } from "@/lib/format";

interface Props {
  candidate: Candidate | null;
  districtNumber: number | null;
  x: number;
  y: number;
}

export default function MapTooltip({
  candidate,
  districtNumber,
  x,
  y,
}: Props) {
  if (districtNumber === null) return null;
  const coh = candidate?.latest_report?.cash_on_hand;
  return (
    <div
      role="tooltip"
      className="absolute pointer-events-none bg-slate-900 text-white text-xs px-3 py-2 rounded-md shadow-lg max-w-[220px] z-10"
      style={{ left: x + 12, top: y + 12 }}
    >
      <div className="font-semibold">{formatDistrict(districtNumber)}</div>
      {candidate ? (
        <>
          <div>{candidate.name}</div>
          <div className="opacity-80 mt-0.5">
            {coh !== undefined && coh !== null
              ? `${formatCurrency(coh)} COH`
              : "Not yet filed"}
          </div>
        </>
      ) : (
        <div className="opacity-70 text-[11px]">No Dem candidate tracked</div>
      )}
    </div>
  );
}
