import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# app.py requires DATABASE_URL at import time.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
