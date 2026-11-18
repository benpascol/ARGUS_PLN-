"""
=============================================================================
PROJECT ARGUS: PORTABLE STANDALONE EXECUTABLE LAUNCHER
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
"""

import os
import sys
import ctypes
from pathlib import Path

# Force unbuffered output agar teks langsung muncul di terminal tanpa delay
os.environ["PYTHONUNBUFFERED"] = "1"

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # Matikan Windows QuickEdit Mode agar terminal tidak macet/freeze jika diklik mouse!
    try:
        kernel32 = ctypes.windll.kernel32
        h_stdin = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE = -10
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_stdin, ctypes.byref(mode)):
            new_mode = mode.value & ~0x0040  # Hapus bit 0x0040 (ENABLE_QUICK_EDIT_MODE)
            kernel32.SetConsoleMode(h_stdin, new_mode)
    except Exception:
        pass

# CETAK HEADER INSTAN DI DETIK PERTAMA SEBELUM IMPORT BERAT
print("\n" + "=" * 78, flush=True)
print("⚡ PT PLN (PERSERO) UNIT INDUK DISTRIBUSI JAWA TIMUR", flush=True)
print("   UP3 MOJOKERTO — SISTEM AUDIT STAND KWH METER (ARGUS v1.0.0 • MODEL V5)", flush=True)
print("=" * 78, flush=True)
print("⏳ Memulai inisialisasi sistem...", flush=True)

# Pastikan root direktori proyek ARGUS masuk ke sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("⏳ Memuat pustaka server & model AI...", flush=True)
    import uvicorn
    from src.api.server import app

    # Jalankan server FastAPI lokal di port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
