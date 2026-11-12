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
4. GET /simulator           : Halaman simulator portal ACMT PLN
5. GET /favicon.ico         : Favicon SVG resmi PLN
6. GET /sample-photo/{path} : Foto sampel meteran dengan fuzzy matcher
=============================================================================
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from src.api.dependencies import BASE_DIR, DASHBOARD_DIR, get_hardware_info

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


@router.get("/favicon.ico")
def get_favicon():
    """Menyajikan favicon SVG resmi ARGUS PLN."""
    fav_path = DASHBOARD_DIR / "static" / "favicon.svg"
    if fav_path.is_file():
        return FileResponse(str(fav_path), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon tidak ditemukan.")


@router.get("/sample-photo/{filename:path}")
def get_sample_photo(filename: str):
    """Menyajikan foto sampel meteran asli dari Docs/DOkumentasi LBKB dengan fallback pencarian cerdas."""
    photo_dir = BASE_DIR / "Docs" / "DOkumentasi LBKB"
    photo_path = photo_dir / filename
    if not photo_path.is_file():
        clean_name = Path(filename).name
        photo_path = photo_dir / clean_name
    if not photo_path.is_file():
        matched = list(photo_dir.glob(f"*{clean_name}*"))
        if not matched and "-" in clean_name:
            parts = clean_name.replace(".jpg", "").replace(".jpeg", "").replace(".png", "").split("-")
            for p in parts:
                if len(p) >= 10 and p.isdigit():
                    matched = list(photo_dir.glob(f"*{p}*.jpg"))
                    if matched:
                        break
        if matched and matched[0].is_file():
            photo_path = matched[0]
        else:
            raise HTTPException(status_code=404, detail=f"Foto {filename} tidak ditemukan di {photo_dir}.")
    return FileResponse(str(photo_path), media_type="image/jpeg")
