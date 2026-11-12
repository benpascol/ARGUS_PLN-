import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import openpyxl
from pathlib import Path

base_dir = Path("ARGUS")
excel_path = base_dir / "data" / "audit_results" / "Audit_LBKB_Result_100_Samples_ModelV4_Refresh.xlsx"
if not excel_path.exists():
    excel_path = base_dir / "data" / "audit_results" / "Audit_LBKB_Result_100_Samples_ModelV4.xlsx"

wb = openpyxl.load_workbook(str(excel_path), data_only=True)
ws = wb["Hasil Audit ARGUS"]

target_cases = [30, 45, 56, 61, 75, 76, 77, 90, 91]
print(f"Inspecting Excel: {excel_path.name}")
print(f"{'NO':<4} | {'IDPEL':<13} | {'NAMA':<20} | {'PLN':<7} | {'ARGUS':<8} | {'VONIS':<16} | {'DIAGNOSA':<30} | {'FILE'}")
print("-" * 125)

for r in range(2, ws.max_row + 1):
    no = ws.cell(row=r, column=1).value
    if no in target_cases:
        idpel = str(ws.cell(row=r, column=2).value or "")
        nama = str(ws.cell(row=r, column=3).value or "")[:20]
        pln = str(ws.cell(row=r, column=6).value or "")
        argus = str(ws.cell(row=r, column=7).value or "")
        vonis = str(ws.cell(row=r, column=9).value or "")
        diagnosa = str(ws.cell(row=r, column=10).value or "")[:30]
        fname = str(ws.cell(row=r, column=18).value or "")
        print(f"{no:<4} | {idpel:<13} | {nama:<20} | {pln:<7} | {argus:<8} | {vonis:<16} | {diagnosa:<30} | {fname}")

