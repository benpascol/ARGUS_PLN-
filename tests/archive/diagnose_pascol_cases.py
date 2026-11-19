import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import cv2
from pathlib import Path
base_dir = Path("ARGUS")
sys.path.insert(0, str(base_dir.resolve()))
from src.vision_ai.pipeline import ArgusVisionPipeline
import openpyxl

pipeline = ArgusVisionPipeline()
excel_path = base_dir / "data" / "audit_results" / "Audit_LBKB_Result_100_Samples_ModelV4_Refresh.xlsx"
wb = openpyxl.load_workbook(str(excel_path), data_only=True)
ws = wb["Hasil Audit ARGUS"]

target_cases = [30, 45, 56, 61, 75, 76, 77, 90, 91]
cases_info = {}
for r in range(2, ws.max_row + 1):
    no = ws.cell(row=r, column=1).value
    if no in target_cases:
        cases_info[no] = {
            "idpel": ws.cell(row=r, column=2).value,
            "nama": ws.cell(row=r, column=3).value,
            "pln": ws.cell(row=r, column=6).value,
            "fname": ws.cell(row=r, column=18).value
        }

print("RUNNING DIAGNOSTIC ON TARGET CASES...")
for no in target_cases:
    info = cases_info.get(no)
    if not info:
        continue
    p = base_dir / "Docs" / "DOkumentasi LBKB" / info["fname"]
    print("\n" + "=" * 80)
    print(f"CASE NO {no} | IDPEL: {info['idpel']} | PLN Stand: {info['pln']}")
    print(f"File: {info['fname']} (exists: {p.exists()})")
    
    if p.exists():
        res = pipeline.predict_image(str(p))
        print(f"  AI Status      : {res.get('status')} | Tier: {res.get('tier_color')}")
        print(f"  AI Reading     : {res.get('reading')}")
        print(f"  Num Digits     : {res.get('num_digits')}")
        print(f"  Span Ratio     : {res.get('span_ratio')}")
        print(f"  Crop Shape     : {res.get('crop_shape')}")
        print(f"  Reason         : {res.get('reason')}")
        print(f"  Digits Detail  :")
        for d in res.get("digits_detail", []):
            print(f"     '{d['digit']}' conf={d['conf']:.2f} x=({d['x1']:.1f}, {d['x2']:.1f})")

