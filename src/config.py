import os
from dotenv import load_dotenv

load_dotenv()

# --- Model ---
MODEL_DIR = "models"
YOLO_MODEL_NAME = "capdi-y8m-640-crowdah-v1-fp32-pt-20250609.pt"

# --- Pipeline ---
SEGMENT_INTERVAL = 5.0  # seconds between PerceptionResult emissions

# Zones: normalized x-axis fractions (left→right)
ZONES: dict[str, tuple[float, float]] = {
    "A": (0.00, 0.33),
    "B": (0.33, 0.67),
    "C": (0.67, 1.00),
}

# --- Trigger ---
HISTORY_WINDOW = 30.0   # seconds of history kept in ring buffer
SURGE_RATIO   = 1.4     # density > avg * this  →  surge trigger
SPEED_MIN     = 0.5     # px/s; below this counts as stagnant
STAG_SEC      = 10.0    # stagnation must persist this many seconds to trigger
ZONE_MAX      = 8       # people in one zone > this  →  hotspot trigger
CONFLICT_SLOPE_MIN = 0.4  # density_slope > this while level=="low"  →  conflict trigger

# Congestion level thresholds (used by trigger/rules.py to set AggregatedFacts.level)
DENSITY_LOW  = 15.0
DENSITY_HIGH = 35.0

# --- Agent ---
AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "anthropic")  # "anthropic" | "gemini"
AGENT_MAX_RETRIES = 3        # API 레벨 실패(네트워크/rate limit/서버 오류) 재시도 횟수
AGENT_RETRY_BACKOFF_SEC = 1.0  # 첫 재시도 대기 시간(초). 매 재시도마다 2배 증가

ANTHROPIC_MODEL = "claude-sonnet-4-6"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
