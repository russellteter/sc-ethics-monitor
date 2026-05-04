export type FilingStatus = "filed" | "not_filed" | "scrape_failed";

export interface LatestReport {
  reportId: string;
  report_type: "Quarterly" | "Initial" | "Pre-Election" | "Final" | "Other";
  period_label: string;
  filed_date: string;
  url: string;
  period_raised: number;
  total_raised: number;
  cash_on_hand: number;
  is_amended: boolean;
}

export interface Candidate {
  id: string;
  name: string;
  district: number;
  party: "D" | "R" | "I" | "O";
  personId: string | null;
  seiId: string | null;
  officeId: string | null;
  filing_status: FilingStatus;
  latest_report: LatestReport | null;
  history: LatestReport[];
  last_error: string | null;
}

export interface Stats {
  total_dem_house: number;
  filed: number;
  not_filed: number;
  scrape_failed: number;
  median_coh: number;
  top_coh: number;
  top_coh_candidate: string | null;
  top_coh_district: number | null;
  total_q_raised: number;
  total_coh_all: number;
}

export interface FinanceArtifact {
  schema_version: number;
  generated_at: string | null;
  cycle: string;
  candidates: Candidate[];
  stats: Stats;
}

export type SortKey =
  | "name"
  | "district"
  | "period_raised"
  | "total_raised"
  | "cash_on_hand"
  | "filed_date";
export type SortDir = "asc" | "desc";
export interface SortState {
  key: SortKey;
  dir: SortDir;
}

export type FilterMode =
  | "all"
  | "filed"
  | "not_filed"
  | "coh_50k_plus"
  | "contested";
