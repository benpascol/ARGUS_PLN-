"""
=============================================================================
PROJECT ARGUS: WEB VIEWS, SYSTEM STATUS & STATIC ASSETS ROUTES
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menyediakan halaman web dan aset statis:
1. GET /                    : Health check status
2. GET /api/system-info     : Deteksi hardware riil GPU RTX / CPU
3. GET /dashboard           : Halaman antarmuka utama Dashboard Modular
4. GET /tutorial            : Halaman panduan operasional & tutorial ARGUS V5
5. GET /simulator           : Halaman simulator portal ACMT PLN
6. GET /favicon.ico         : Favicon SVG resmi PLN
7. GET /sample-photo/{path} : Foto sampel meteran dengan fuzzy matcher
=============================================================================
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

# Pastikan root direktori proyek ARGUS masuk ke sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.api.dependencies import BASE_DIR, DASHBOARD_DIR, get_hardware_info, resolve_photo_path

router = APIRouter(tags=["Web Views & System Status"])

# Jinja2 Templates Setup
templates = Jinja2Templates(directory=str(DASHBOARD_DIR)) if DASHBOARD_DIR.is_dir() else None


@router.get("/")
def root():
    """Health check & status engine."""
    return {
        "app": "Project ARGUS AI Vision Engine",
        "unit": "PT PLN (Persero) UP3 Mojokerto",
        "lead_engineer": "Benedictus Pascal",
        "status": "ONLINE",
        "mode": "100% Pure Local & Offline",
        "version": "1.0.0"
    }


@router.get("/api/system-info")
def get_system_info():
    """Mengembalikan informasi hardware komputasi riil (GPU RTX / CPU) dan konfigurasi engine ARGUS."""
    hw = get_hardware_info()
    return {
        "app": "Project ARGUS AI Vision Engine",
        "unit": "PT PLN (Persero) UP3 Mojokerto",
        "lead_engineer": "Benedictus Pascal",
        "hardware": hw
    }


@router.get("/simulator", response_class=HTMLResponse)
def get_simulator():
    """Halaman Simulator Portal ACMT PLN untuk Uji Coba Evaluasi & Tampermonkey."""
    sim_path = BASE_DIR / "web_extension" / "simulator.html"
    if not sim_path.is_file():
        raise HTTPException(status_code=404, detail="Berkas simulator.html tidak ditemukan.")
    return HTMLResponse(content=sim_path.read_text(encoding="utf-8"))


@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    """Halaman Standalone Web Dashboard ARGUS (Modular Component Architecture)."""
    if templates and (DASHBOARD_DIR / "index.html").is_file():
        return templates.TemplateResponse(request=request, name="index.html")
    dash_path = BASE_DIR / "web_extension" / "dashboard.html"
    if dash_path.is_file():
        return HTMLResponse(content=dash_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Berkas dashboard tidak ditemukan.")


@router.get("/tutorial", response_class=HTMLResponse)
def get_tutorial(request: Request):
    """Halaman Panduan & Tutorial Operasional ARGUS V5 untuk Tim PLN UP3 Mojokerto."""
    tutorial_path = DASHBOARD_DIR / "tutorial.html"
    if templates and tutorial_path.is_file():
        return templates.TemplateResponse(request=request, name="tutorial.html")
    if tutorial_path.is_file():
        return HTMLResponse(content=tutorial_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Berkas tutorial.html tidak ditemukan.")


@router.get("/favicon.ico")
def get_favicon():
    """Menyajikan favicon SVG resmi ARGUS PLN."""
    fav_path = DASHBOARD_DIR / "static" / "favicon.svg"
    if fav_path.is_file():
        return FileResponse(str(fav_path), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon tidak ditemukan.")


@router.get("/sample-photo/{filename:path}")
def get_sample_photo(filename: str):
    """Menyajikan foto sampel meteran asli dengan fallback pencarian cerdas di data/input_foto & Docs/DOkumentasi LBKB."""
    photo_path = resolve_photo_path(filename)
    if not photo_path or not photo_path.is_file():
        raise HTTPException(status_code=404, detail=f"Foto {filename} tidak ditemukan di folder penyimpanan data.")
    return FileResponse(str(photo_path), media_type="image/jpeg")
