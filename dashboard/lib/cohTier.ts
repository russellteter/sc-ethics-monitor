export function cohTier(coh: number | null): 0 | 1 | 2 | 3 | 4 {
  if (coh === null || coh === undefined || coh <= 0) return 0;
  if (coh < 10_000) return 1;
  if (coh < 50_000) return 2;
  if (coh < 100_000) return 3;
  return 4;
}

const COLORS: Record<number, string> = {
  0: "#E0F7F4",
  1: "#9DE5DC",
  2: "#5CD4C8",
  3: "#1ED4C2",
  4: "#1A4A45",
};

const LABELS: Record<number, string> = {
  0: "$0",
  1: "<$10K",
  2: "$10–50K",
  3: "$50–100K",
  4: "$100K+",
};

export function cohTierColor(t: 0 | 1 | 2 | 3 | 4): string {
  return COLORS[t];
}
export function cohTierLabel(t: 0 | 1 | 2 | 3 | 4): string {
  return LABELS[t];
}
