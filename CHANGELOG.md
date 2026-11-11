# Changelog — Project ARGUS

All notable changes to **Project ARGUS (Automated Recognition & Grid Utility Surveillance)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).  
*Note: As this project is currently in active pre-release development, versions adhere to the `0.y.z` pre-release specification prior to the official v1.0.0 production deployment.*

**Lead Engineer:** Pascol  
**Institution:** PT PLN (Persero) UP3 Mojokerto  

---

## [Unreleased]
### Added
- Architectural roadmap for Standalone Audit Dashboard (`Docs/WHITEBOARD_DASHBOARD_ROADMAP.md`).
- Planning for automated Excel-Photo Pairing mechanism to ingest ACMT master sheets without manual stan entry.
- Virtual DOM / Pagination blueprint to handle large-scale batch photo rendering (7,000+ files) with minimal browser RAM footprint.

---

## [0.5.0] - 2026-11-07
### Added
- **Multi-Scale Production Benchmark:** Comprehensive multi-scale evaluation across 500, 2,500, 5,000, and 7,470 samples comparing Model V5 vs Model V4.
- **Standalone Corporate Dashboard (`dashboard.html`):** 100% Light Theme UI aligned with official PLN corporate branding (`#007BB5` PLN Blue, `#FDB913` Lightning Yellow), featuring interactive KPI filter cards and real-time client-side search.
- **Human-in-the-Loop Audit Capabilities:** Interactive editable fields for AI reading correction, audit verdict dropdowns (`MATCH`, `ROLLING`, `DIFF`, `NIHIL`, `TRIAGE`), and auditor notes input.
- **ACMT Portal Simulator (`simulator.html`):** High-fidelity local simulation environment for Tampermonkey userscript evaluation without requiring external VPN access.
- **Official Excel Export API (`/api/export-audit-excel`):** Backend endpoint connected directly to `openpyxl` engine for generating 19-column audit sheets with active clickable `=HYPERLINK(...)` formulas.

### Changed
- Refined confidence gates and consensus scoring for LCD screen reflection suppression.

### Performance
- Achieved **3,854 Matches (51.59% total / 71.24% on valid physical meters)** across 7,470 full-scale production dataset.
- Inference latency reduced by 43.1% to **78.3 ms/meter** on NVIDIA GeForce RTX 4060 GPU.

---

## [0.4.0] - 2026-11-05
### Added
- **Official PLN Audit Excel Engine (`src/audit_excel.py`):** Automated report generator implementing UP3 Mojokerto's 4-line executive legend and structured formatting.
- **Multi-Candidate Digit Consensus:** Consensus voting mechanism across bounding box overlaps to prevent single-digit misreads on degraded dials.
- **Strict Rolling Digit Guard:** Deterministic handling for mechanical drum transitions within $\pm 1$ to $\pm 2$ kWh threshold.
- **Focused Audit Trail Mode:** Memory-efficient logging to prevent RAM exhaustion during extensive batch runs.

---

## [0.3.0] - 2026-11-02
### Added
- **Local FastAPI REST Engine (`src/api/server.py`):** High-throughput, 100% offline backend serving `/predict` (Multipart) and `/predict-base64` (JSON) endpoints.
- **Enterprise Userscript Extension (`web_extension/argus_evaluator.user.js`):** Tampermonkey integration for real-time verification directly within PLN's ACMT web portal (`portalapp.iconpln.co.id`).
- **Heuristic Zero-Counter Anti-Fraud:** Stage-1 YOLO fallback (`FAIL_COUNTER_NOT_FOUND`) immediately rejecting non-meter imagery (pavement, motorbike seats, fences) without digit hallucination.

---

## [0.2.0] - 2026-10-28
### Added
- **Two-Stage YOLO Vision Pipeline:**
  - Stage 1: `meter_counter_detector.pt` for counter dial ROI localization and cropping.
  - Stage 2: `digit_ocr_detector.pt` for sequence-aware digit recognition (`0–9`) and decimal dot detection.
- **Spatial Sequence Validator:** Sorting and continuity validation enforcing unbroken digit strings for electromechanical meters.
- **Decimal Dot Splitter:** Logic separating whole kWh values from fractional decimals on digital meters.

---

## [0.1.0] - 2026-09-26
### Added
- **Scientific Foundation & Architecture:** Cascading Multi-Tier Computer Vision framework documented in `Docs/ARGUS_Research_Validation.md`.
- **Quality Gatekeeper (Tier 1):** OpenCV Laplacian variance filter for low-focus/blur detection and HSV V/S thresholding for specular glare rejection.
- **Barcode Decoding Engine (Tier 2A):** ZBar barcode reader enhanced with CLAHE contrast equalization for prepaid meter serial numbers.
- **Engineering Roadmap:** Formalization of 7-step Machine Learning Lifecycle (MLLC) in `Docs/ARGUS_Methodology_Roadmap.md`.

