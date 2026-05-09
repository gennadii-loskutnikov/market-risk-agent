import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

_db_path = os.getenv("DATABASE_PATH", "data/market_data.sqlite")
DATABASE_PATH = str(PROJECT_ROOT / _db_path) if not os.path.isabs(_db_path) else _db_path

STARTUP_PREFETCH_LIMIT = int(os.getenv("STARTUP_PREFETCH_LIMIT", "5"))

FRESHNESS_RULES = {
    "market_signals": 15 * 60,
    "ticker_snapshot": 15 * 60,
    "price_history": 24 * 60 * 60,
    "recommendations": 24 * 60 * 60,
    "related_companies": 7 * 24 * 60 * 60,
}
