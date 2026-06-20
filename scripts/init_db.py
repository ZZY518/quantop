from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import init_db  # noqa: E402


if __name__ == "__main__":
    init_db()
    print(f"database initialized: {ROOT / 'data' / 'quantop.db'}")
