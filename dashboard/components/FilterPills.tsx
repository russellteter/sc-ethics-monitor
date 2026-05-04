"use client";
import type { FilterMode } from "@/lib/types";

const PILLS: { value: FilterMode; label: string }[] = [
  { value: "all", label: "All districts" },
  { value: "filed", label: "Filed only" },
  { value: "not_filed", label: "Not filed" },
  { value: "coh_50k_plus", label: "COH ≥ $50K" },
  { value: "contested", label: "Contested" },
];

interface Props {
  value: FilterMode;
  onChange: (v: FilterMode) => void;
}

export default function FilterPills({ value, onChange }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {PILLS.map((p) => (
        <button
          key={p.value}
          type="button"
          onClick={() => onChange(p.value)}
          className={
            "px-3 py-1 text-xs rounded-full border transition " +
            (value === p.value
              ? "bg-teal-deep text-white border-teal-deep"
              : "bg-bg border-line text-ink hover:border-teal-primary")
          }
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
