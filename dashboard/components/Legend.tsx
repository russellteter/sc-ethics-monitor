import { cohTierColor, cohTierLabel } from "@/lib/cohTier";

export default function Legend() {
  return (
    <div className="px-4 py-3 border-t border-line text-[11px] text-muted flex flex-wrap gap-x-2 gap-y-1 items-center">
      <span className="mr-1">COH tier:</span>
      {[0, 1, 2, 3, 4].map((t) => (
        <span key={t} className="inline-flex items-center gap-1">
          <span
            className="inline-block w-3 h-3 rounded-sm align-middle"
            style={{ background: cohTierColor(t as 0 | 1 | 2 | 3 | 4) }}
          />
          {cohTierLabel(t as 0 | 1 | 2 | 3 | 4)}
        </span>
      ))}
    </div>
  );
}
