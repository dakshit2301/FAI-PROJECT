"""Start the local Lost Item Recovery Agent website."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from web.server import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
