import type { FilingStatus } from "@/lib/types";

const STYLES: Record<FilingStatus, string> = {
  filed: "bg-blue-100 text-blue-800 border-blue-300",
  not_filed: "bg-slate-100 text-slate-600 border-slate-300",
  scrape_failed: "bg-amber-50 text-amber-700 border-amber-300",
};

const LABEL: Record<FilingStatus, string> = {
  filed: "Filed",
  not_filed: "Not filed",
  scrape_failed: "Error",
};

interface Props {
  status: FilingStatus;
}

export default function StatusBadge({ status }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${STYLES[status]}`}
    >
      {LABEL[status]}
    </span>
  );
}
