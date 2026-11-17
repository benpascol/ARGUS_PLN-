"""
=============================================================================
PROJECT ARGUS: AUTOMATED STANDALONE BUILD SCRIPT (PYINSTALLER ONEDIR)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Membangun paket aplikasi portabel mandiri:
1. Mengompilasi launcher.py menjadi dist/ARGUS/ARGUS.exe
2. Mengumpulkan modul YOLO, PyTorch CUDA, Uvicorn, FastAPI, openpyxl, OpenCV
3. Menyinkronkan aset models/ dan web_extension/ ke direktori dist/ARGUS/
=============================================================================
"""

import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("=" * 80)
    print("⚡ PROJECT ARGUS - PEMBUATAN PAKET PORTABLE EXECUTABLE (ONEDIR)")
    print("   PT PLN (Persero) UP3 Mojokerto")
    print("=" * 80)

    # 1. Pastikan PyInstaller terpasang di venv
    try:
        import PyInstaller
        print(f"📦 PyInstaller Terdeteksi: Versi {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller belum terpasang di virtual environment!")
        sys.exit(1)

    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"
    app_dist_dir = dist_dir / "ARGUS"

    print("\n🧹 Membersihkan build cache lama jika ada...")
    if app_dist_dir.exists():
        shutil.rmtree(app_dist_dir, ignore_errors=True)

    # 2. Argumen PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ARGUS",
        "--onedir",
        "--console",
        "--clean",
        "--noconfirm",
        f"--icon={str(BASE_DIR / 'ARGUS.ico')}",
        "--collect-all=ultralytics",
        "--collect-all=uvicorn",
        "--collect-all=fastapi",
        "--collect-all=starlette",
        "--collect-all=pydantic",
        "--hidden-import=torch",
        "--hidden-import=torchvision",
        "--hidden-import=openpyxl",
        "--hidden-import=cv2",
        "--hidden-import=jinja2",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespans.on",
        str(BASE_DIR / "launcher.py")
    ]

    print("\n🚀 Menjalankan PyInstaller (Proses ini memakan waktu 1-3 menit untuk memaketkan CUDA PyTorch)...")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    if result.returncode != 0:
        print("\n❌ Proses PyInstaller gagal dengan kode keluar non-zero!")
        sys.exit(result.returncode)

    print("\n✅ Kompilasi Biner Selesai! Menyalin Aset Pendukung...")

    # 3. Salin Folder Models
    target_models = app_dist_dir / "models"
    target_models.mkdir(parents=True, exist_ok=True)
    src_models = BASE_DIR / "models"
    for pt_file in src_models.glob("*.pt"):
        dest_file = target_models / pt_file.name
        print(f"   [+] Menyalin model: {pt_file.name} -> {dest_file.relative_to(dist_dir)}")
        shutil.copy2(pt_file, dest_file)

    # 4. Salin Web Extension & Dashboard
    target_web = app_dist_dir / "web_extension"
    target_web.mkdir(parents=True, exist_ok=True)
    src_web = BASE_DIR / "web_extension"

    # Dashboard folder
    dest_dashboard = target_web / "dashboard"
    if dest_dashboard.exists():
        shutil.rmtree(dest_dashboard)
    shutil.copytree(src_web / "dashboard", dest_dashboard)
    print("   [+] Menyalin antarmuka Dashboard Web (HTML, CSS, JS)...")

    # Simulator & userscript jika ada
    if (src_web / "simulator.html").is_file():
        shutil.copy2(src_web / "simulator.html", target_web / "simulator.html")
    if (src_web / "argus_evaluator.user.js").is_file():
        shutil.copy2(src_web / "argus_evaluator.user.js", target_web / "argus_evaluator.user.js")

    # 5. Siapkan struktur folder data/
    (app_dist_dir / "data" / "input_foto").mkdir(parents=True, exist_ok=True)
    (app_dist_dir / "data" / "input_excel").mkdir(parents=True, exist_ok=True)
    (app_dist_dir / "data" / "audit_results").mkdir(parents=True, exist_ok=True)
    (app_dist_dir / "data" / "samples").mkdir(parents=True, exist_ok=True)
    (app_dist_dir / "data" / "feedback_staging").mkdir(parents=True, exist_ok=True)
    (app_dist_dir / "data" / "feedback_releases").mkdir(parents=True, exist_ok=True)

    # Salin README panduan input folder
    if (BASE_DIR / "data" / "input_foto" / "BACA_SAYA.txt").is_file():
        shutil.copy2(BASE_DIR / "data" / "input_foto" / "BACA_SAYA.txt", app_dist_dir / "data" / "input_foto" / "BACA_SAYA.txt")
    if (BASE_DIR / "data" / "input_excel" / "BACA_SAYA.txt").is_file():
        shutil.copy2(BASE_DIR / "data" / "input_excel" / "BACA_SAYA.txt", app_dist_dir / "data" / "input_excel" / "BACA_SAYA.txt")

    # Salin beberapa contoh sampel jika ada
    samples_src = BASE_DIR / "data" / "samples"
    if samples_src.is_dir():
        for s in list(samples_src.glob("*.jpg"))[:5]:
            shutil.copy2(s, app_dist_dir / "data" / "samples" / s.name)
        print("   [+] Menyalin contoh sampel foto meteran...")

    # 6. Salin Dokumen Panduan Penggunaan Lengkap
    if (BASE_DIR / "PETUNJUK_PENGGUNAAN_ARGUS.txt").is_file():
        shutil.copy2(BASE_DIR / "PETUNJUK_PENGGUNAAN_ARGUS.txt", app_dist_dir / "PETUNJUK_PENGGUNAAN_ARGUS.txt")
        print("   [+] Menyalin PETUNJUK_PENGGUNAAN_ARGUS.txt...")

    # 7. Buat file batch launcher praktis (Dashboard & Panduan Tutorial)
    bat_content = (
        "@echo off\n"
        "title ARGUS AI Vision - PT PLN (Persero) UP3 Mojokerto\n"
        "cd /d \"%~dp0\"\n"
        "start \"\" \"%~dp0ARGUS.exe\"\n"
    )
    (app_dist_dir / "Mulai_ARGUS.bat").write_text(bat_content, encoding="utf-8")

    tutorial_bat_content = (
        "@echo off\n"
        "title Panduan ARGUS AI V5 - PT PLN (Persero) UP3 Mojokerto\n"
        "cd /d \"%~dp0\"\n"
        "powershell -NoProfile -Command \"$ok = $false; try { $c = New-Object System.Net.Sockets.TcpClient; $ar = $c.BeginConnect('127.0.0.1', 8000, $null, $null); if ($ar.AsyncWaitHandle.WaitOne(250)) { $c.EndConnect($ar); $ok = $true }; $c.Close() } catch {}; if ($ok) { exit 0 } else { exit 1 }\"\n"
        "if %errorlevel%==0 (\n"
        "    start \"\" \"http://127.0.0.1:8000/tutorial\"\n"
        "    exit /b 0\n"
        ")\n"
        "echo Menyalakan engine ARGUS terlebih dahulu untuk membuka Panduan Interaktif...\n"
        "start \"\" \"%~dp0ARGUS.exe\"\n"
        "powershell -NoProfile -Command \"for ($i=0; $i -lt 60; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/tutorial' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { Start-Process 'http://127.0.0.1:8000/tutorial'; exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; Start-Process 'http://127.0.0.1:8000/tutorial'\"\n"
    )
    (app_dist_dir / "Buka_Panduan_ARGUS.bat").write_text(tutorial_bat_content, encoding="utf-8")

    print("\n" + "=" * 80)
    print("🎉 SUKSES! PAKET APLIKASI PORTABLE ARGUS SELESAI DIBANGUN!")
    print("=" * 80)
    print(f"📁 Lokasi Folder Distribusi:")
    print(f"   {app_dist_dir.resolve()}")
    print("\n💡 Cara Menjalankan:")
    print(f"   1. Buka folder di atas di File Explorer.")
    print(f"   2. Klik ganda pada berkas 'ARGUS.exe' (atau 'Mulai_ARGUS.bat').")
    print("   3. Jendela terminal PLN akan terbuka, dan browser akan otomatis menuju ke:")
    print("      http://127.0.0.1:8000/dashboard")
    print("   4. Untuk membaca tutorial lengkap di browser, klik ganda 'Buka_Panduan_ARGUS.bat'")
    print("      (atau buka http://127.0.0.1:8000/tutorial).")
    print("=" * 80)

if __name__ == "__main__":
    build()

