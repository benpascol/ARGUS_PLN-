"""
=============================================================================
PROJECT ARGUS: PORTABLE STANDALONE EXECUTABLE LAUNCHER
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
"""

import sys
from pathlib import Path

# Pastikan root direktori proyek ARGUS masuk ke sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if __name__ == "__main__":
    import uvicorn
    from src.api.server import app

    # Jalankan server FastAPI lokal di port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

