from pathlib import Path
from re import IGNORECASE, compile

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
HOUSE_FINANCE_PATH = DATA_DIR / "house_finance.json"
PERSONID_CACHE_PATH = DATA_DIR / "personId_cache.json"

VREMS_REPO_PATH = REPO_ROOT.parent / "sc-vrems-filing-monitor"
VREMS_STATE_PATH = VREMS_REPO_PATH / "state.json"
ETHICS_STATE_PATH = REPO_ROOT / "state.json"

ETHICS_BASE = "https://ethicsfiling.sc.gov"
ETHICS_REPORTS_LIST = ETHICS_BASE + "/public/candidates-public-officials/person/campaign-disclosure-reports"
ETHICS_REPORT_DETAIL = ETHICS_BASE + "/public/candidates-public-officials/person/campaign-disclosure-reports/report-detail"

USER_AGENT = "Mozilla/5.0 (compatible; LocalityAI-FinanceMonitor/1.0)"

STATE_HOUSE_PATTERNS = [
    compile(r"sc house of representatives", IGNORECASE),
    compile(r"house of representatives district", IGNORECASE),
]

REQUEST_TIMEOUT_SEC = 30
RETRY_MAX = 4
RETRY_BACKOFF_BASE_SEC = 1.0
INTER_REQUEST_DELAY_SEC = 1.0

COH_TIERS = [
    (0, "no-funds"),
    (1, "under-10k"),
    (10_000, "10-50k"),
    (50_000, "50-100k"),
    (100_000, "100k-plus"),
]

SCHEMA_VERSION = 1
