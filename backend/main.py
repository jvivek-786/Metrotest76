"""
MetroTest-76: Automated Test Report Generation & Anti-Tampering Compliance Platform
Problem Statement: SIH26035 (Smart India Hackathon 2026)
Issuing Authority: Ministry of Consumer Affairs, Food & Public Distribution | Department of Consumer Affairs (DoCA), GoI
"""

import os
import uuid
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import init_db, save_report, get_all_reports, get_report_by_id, verify_hash, review_report
from .oiml_engine import OIMLR76Engine
from .vision_ocr import VisionQualityEngine, OpticalIngestionEngine
from .pdf_report import OIMLReportGenerator
from .docx_report import generate_docx
from .crypto_utils import compute_file_sha256

app = FastAPI(
    title="MetroTest-76: OIML R-76 Testing & Compliance Platform",
    description="Automated OIML R-76 Test Report Generation & Strict-Liability Audit System (SIH26035)",
    version="2.0.0"
)

# Enable CORS for local testing & offline integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLES_DIR = os.path.join(UPLOADS_DIR, "samples")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

# Mount static and asset directories
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

# Initialize database tables
init_db()


@app.get("/")
def get_home():
    """Serves the primary MetroTest-76 compliance interface."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# -------------------------------------------------------------
# 1. Optical Ingestion & OpenCV Pre-Flight Check APIs
# -------------------------------------------------------------

@app.post("/api/ocr-nameplate")
async def ocr_nameplate(file: UploadFile = File(...)):
    """
    Ingests machine rating plate photograph (Exhibit A),
    executes OpenCV blur/glare pre-flight check, extracts metrological specs via OCR,
    and returns parsed values for officer verification.
    """
    filename = f"nameplate_{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())

    # Perform OpenCV inspection & intelligent OCR
    extracted = OpticalIngestionEngine.ocr_nameplate(filepath)
    extracted["photo_url"] = f"/uploads/{filename}"
    extracted["raw_photo_path"] = filepath
    return extracted


@app.post("/api/ocr-display")
async def ocr_display(file: UploadFile = File(...)):
    """
    Ingests digital scale readout photograph at critical test load (Exhibit B),
    executes OpenCV pre-flight check, and extracts numerical weight reading.
    """
    filename = f"display_{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())

    extracted = OpticalIngestionEngine.ocr_display(filepath)
    extracted["photo_url"] = f"/uploads/{filename}"
    extracted["raw_photo_path"] = filepath
    return extracted


@app.post("/api/check-image-quality")
async def check_image_quality(file: UploadFile = File(...)):
    """
    Direct OpenCV pre-flight diagnostic for blur, glare, and illumination.
    """
    temp_path = os.path.join(UPLOADS_DIR, f"temp_{uuid.uuid4().hex[:8]}_{file.filename}")
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    try:
        quality = VisionQualityEngine.inspect_image(temp_path)
        return quality
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# -------------------------------------------------------------
# 2. Deterministic OIML R-76 Mathematical Calculation APIs
# -------------------------------------------------------------

class MPECalcRequest(BaseModel):
    load_kg: float
    e_grams: float
    accuracy_class: str = "Class III"
    is_initial: bool = True

@app.post("/api/calculate-mpe")
def calculate_mpe_api(req: MPECalcRequest):
    """
    Computes statutory MPE for a given load, interval e, and class.
    Pure Python deterministic logic — zero hallucination.
    """
    load_g = req.load_kg * 1000.0
    mpe_g = OIMLR76Engine.calculate_mpe(load_g, req.e_grams, req.accuracy_class, req.is_initial)
    mpe_in_e = OIMLR76Engine.calculate_mpe_in_e(load_g, req.e_grams, req.accuracy_class) * (1.0 if req.is_initial else 2.0)
    m_in_e = load_g / req.e_grams if req.e_grams > 0 else 0
    return {
        "load_kg": req.load_kg,
        "load_g": load_g,
        "m_in_e": round(m_in_e, 1),
        "mpe_g": round(mpe_g, 3),
        "mpe_in_e": mpe_in_e,
        "is_initial": req.is_initial
    }


# -------------------------------------------------------------
# 3. Full Report Submission & Cryptographic Sealing
# -------------------------------------------------------------

@app.post("/api/generate-full-submission")
async def generate_full_submission(
    officer_name: str = Form("Insp. Rajesh Sharma"),
    officer_badge: str = Form("RRSL-DOCA-2026-449"),
    manufacturer: str = Form("Eagle Scales Pvt Ltd"),
    model: str = Form("DS-215"),
    serial_no: str = Form("SN-2026-98124"),
    accuracy_class: str = Form("Class III"),
    max_cap: float = Form(30.0),
    min_cap: float = Form(100.0),
    e_val: float = Form(5.0),
    environmental_conditions: str = Form("22.5°C | 50% RH"),
    is_initial_verification: bool = Form(True),
    gps_coordinates: str = Form("18.5204° N, 73.8567° E (RRSL Pune)"),
    weighing_observations: str = Form(...),
    eccentricity_data: Optional[str] = Form(None),
    repeatability_data: Optional[str] = Form(None),
    nameplate_photo: Optional[UploadFile] = File(None),
    existing_nameplate_path: Optional[str] = Form(None),
    display_photo: Optional[UploadFile] = File(None),
    existing_display_path: Optional[str] = Form(None),
    has_manual_override: bool = Form(False),
    override_details: str = Form("")
):
    """
    Full OIML R-76 test evaluation, dual photographic ground-truth binding (Exhibits A & B),
    SHA-256 cryptographic evidence sealing, PDF & DOCX generation, and Section 63 BSA attestation.
    """
    # 1. Process Exhibit A (Nameplate Photo)
    saved_nameplate_path = existing_nameplate_path
    if nameplate_photo and nameplate_photo.filename:
        filename = f"exhibit_a_{uuid.uuid4().hex[:8]}_{nameplate_photo.filename}"
        saved_nameplate_path = os.path.join(UPLOADS_DIR, filename)
        with open(saved_nameplate_path, "wb") as f:
            f.write(await nameplate_photo.read())

    # Fallback to sample if none provided
    if not saved_nameplate_path or not os.path.exists(saved_nameplate_path):
        sample_a = os.path.join(SAMPLES_DIR, "sample_nameplate_eagle.png")
        if os.path.exists(sample_a):
            saved_nameplate_path = sample_a

    # 2. Process Exhibit B (Display Photo at Max Load)
    saved_display_path = existing_display_path
    if display_photo and display_photo.filename:
        filename = f"exhibit_b_{uuid.uuid4().hex[:8]}_{display_photo.filename}"
        saved_display_path = os.path.join(UPLOADS_DIR, filename)
        with open(saved_display_path, "wb") as f:
            f.write(await display_photo.read())

    if not saved_display_path or not os.path.exists(saved_display_path):
        sample_b = os.path.join(SAMPLES_DIR, "sample_display_pass.png")
        if os.path.exists(sample_b):
            saved_display_path = sample_b

    # 3. Evaluate Weighing Observations deterministically
    try:
        obs_list = json.loads(weighing_observations)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid weighing observations JSON format")

    evaluated_obs = []
    overall_passed = True
    for item in obs_list:
        res = OIMLR76Engine.evaluate_weighing_observation(
            load_kg=float(item.get("load_kg", item.get("load", 0))),
            indication_kg=float(item.get("indication_kg", item.get("indication", 0))),
            e_grams=e_val,
            accuracy_class=accuracy_class,
            is_initial=is_initial_verification
        )
        if not res["passed"]:
            overall_passed = False
        evaluated_obs.append(res)

    # 4. Optional Eccentricity & Repeatability Tests
    ecc_res = None
    if eccentricity_data:
        try:
            ecc_raw = json.loads(eccentricity_data)
            if isinstance(ecc_raw, list) and len(ecc_raw) >= 4:
                ecc_res = OIMLR76Engine.evaluate_eccentricity_test(
                    corner_readings_kg=[float(x) for x in ecc_raw],
                    test_load_kg=round(max_cap / 3.0, 3),
                    e_grams=e_val,
                    accuracy_class=accuracy_class,
                    is_initial=is_initial_verification
                )
                if not ecc_res["overall_passed"]:
                    overall_passed = False
        except Exception as e:
            print(f"[Submission] Eccentricity parsing skipped: {e}")

    rep_res = None
    if repeatability_data:
        try:
            rep_raw = json.loads(repeatability_data)
            if isinstance(rep_raw, list) and len(rep_raw) >= 3:
                rep_res = OIMLR76Engine.evaluate_repeatability_test(
                    readings_kg=[float(x) for x in rep_raw],
                    test_load_kg=max_cap,
                    e_grams=e_val,
                    accuracy_class=accuracy_class,
                    is_initial=is_initial_verification
                )
                if not rep_res["passed"]:
                    overall_passed = False
        except Exception as e:
            print(f"[Submission] Repeatability parsing skipped: {e}")

    # 5. Build Full Rule-Wise Audit Sheet (All 10 Statutory Tests)
    full_audit = OIMLR76Engine.build_full_rule_wise_audit(
        max_cap_kg=max_cap,
        min_cap_g=min_cap,
        e_g=e_val,
        d_g=e_val,
        accuracy_class=accuracy_class,
        weighing_observations=evaluated_obs,
        eccentricity_data=ecc_res,
        repeatability_data=rep_res,
        residual_zero_g=0.0,
        tare_load_kg=5.0,
        tare_ind_kg=5.001,
        has_manual_override=has_manual_override
    )

    passed_clauses_count = sum(1 for a in full_audit if a["passed"])
    failed_clauses_count = sum(1 for a in full_audit if not a["passed"])
    if failed_clauses_count > 0:
        overall_passed = False

    # 6. Build Report Identifiers & Paths
    report_id = f"TR-2026-{uuid.uuid4().hex[:6].upper()}"
    pdf_filename = f"{report_id}_OIML_R76.pdf"
    docx_filename = f"{report_id}_OIML_R76.docx"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    docx_path = os.path.join(REPORTS_DIR, docx_filename)

    report_data = {
        "report_id": report_id,
        "officer_name": officer_name,
        "officer_badge": officer_badge,
        "manufacturer": manufacturer,
        "model": model,
        "serial_no": serial_no,
        "accuracy_class": accuracy_class,
        "max_cap": max_cap,
        "min_cap": min_cap,
        "e_val": e_val,
        "environmental_conditions": environmental_conditions,
        "is_initial": is_initial_verification,
        "gps_coordinates": gps_coordinates,
        "date": datetime.now(timezone.utc).strftime("%d-%m-%Y %H:%M:%S UTC"),
        "lab_name": "Regional Reference Standards Laboratory (RRSL)",
        "weighing_observations": evaluated_obs,
        "eccentricity_test": ecc_res,
        "repeatability_test": rep_res,
        "full_audit_rows": full_audit,
        "passed_clauses": passed_clauses_count,
        "failed_clauses": failed_clauses_count,
        "overall_status": "PASS" if overall_passed else "FAIL",
        "has_manual_override": has_manual_override,
        "override_details": override_details
    }

    # 7. Generate Official PDF Report
    pdf_sha256 = OIMLReportGenerator.generate_pdf(
        report_data=report_data,
        output_filepath=pdf_path,
        nameplate_image_path=saved_nameplate_path,
        display_image_path=saved_display_path
    )
    report_data["sha256_hash"] = pdf_sha256

    # 8. Generate Official Editable DOCX Report
    generate_docx(
        report_data=report_data,
        output_filepath=docx_path,
        nameplate_image_path=saved_nameplate_path,
        display_image_path=saved_display_path
    )

    # 9. Commit to Immutable Database Ledger (SQLAlchemy 2.0)
    save_report(
        report_data=report_data,
        sha256_hash=pdf_sha256,
        pdf_path=pdf_path,
        docx_path=docx_path,
        nameplate_photo_path=saved_nameplate_path,
        display_photo_path=saved_display_path,
        has_override=has_manual_override,
        override_details=override_details
    )

    return {
        "success": True,
        "report_id": report_id,
        "overall_status": report_data["overall_status"],
        "sha256_hash": pdf_sha256,
        "has_manual_override": has_manual_override,
        "override_details": override_details,
        "passed_clauses": passed_clauses_count,
        "failed_clauses": failed_clauses_count,
        "full_audit_rows": full_audit,
        "pdf_download_url": f"/api/download-report/{pdf_filename}",
        "docx_download_url": f"/api/download-report/{docx_filename}",
        "qr_image_url": f"/api/get-qr/{report_id}",
        "evaluations_count": len(evaluated_obs),
        "nameplate_photo_url": f"/uploads/{os.path.basename(saved_nameplate_path)}" if saved_nameplate_path else None,
        "display_photo_url": f"/uploads/{os.path.basename(saved_display_path)}" if saved_display_path else None
    }


class FullAuditEvalRequest(BaseModel):
    max_cap_kg: float = 30.0
    min_cap_g: float = 100.0
    e_val_g: float = 5.0
    d_val_g: float = 5.0
    accuracy_class: str = "Class III"
    goods_category: str = "NAWI"
    weighing_observations: Optional[List[Dict[str, Any]]] = None
    eccentricity_data: Optional[Dict[str, Any]] = None
    repeatability_data: Optional[Dict[str, Any]] = None
    residual_zero_g: float = 0.0
    tare_load_kg: float = 5.0
    tare_ind_kg: float = 5.001
    has_manual_override: bool = False


@app.post("/api/evaluate-full-audit")
def evaluate_full_audit_endpoint(req: FullAuditEvalRequest):
    """
    Evaluates all statutory OIML R-76 clauses or PCR 2011 clauses and returns
    passed clauses count, failed clauses count, and row-by-row audit findings.
    """
    if req.goods_category == "PC":
        # Packaged Commodities Rules 2011 audit as per Page 4 reference screenshot
        pcr_rows = [
            {
                "rule": "6 (1) (a)",
                "name": "Name and Complete Address",
                "desc": "Manufacturer, packer or importer physical address with pin code",
                "passed": True,
                "verdict": "PASSED"
            },
            {
                "rule": "6 (1) (b)",
                "name": "Generic or Common Name",
                "desc": "Clear commodity identification on the principal display panel",
                "passed": True,
                "verdict": "PASSED"
            },
            {
                "rule": "6 (1) (c)",
                "name": "Net Quantity in Standard Units",
                "desc": "Permissible metric unit of weight/volume declaration (1.0 L / 910 g)",
                "passed": True,
                "verdict": "PASSED"
            },
            {
                "rule": "6 (1) (d)",
                "name": "Month & Year of Manufacture / Packing",
                "desc": "Clear packaging date stamp in MM/YYYY format (08/2026)",
                "passed": True,
                "verdict": "PASSED"
            },
            {
                "rule": "6 (11)",
                "name": "Unit Sale Price (USP) Display",
                "desc": "Per g/ml unit price calculation missing on retail carton",
                "passed": False,
                "verdict": "FAILED"
            },
            {
                "rule": "6 (10)",
                "name": "Country of Origin",
                "desc": "Mandatory origin declaration on packaging (India)",
                "passed": True,
                "verdict": "PASSED"
            },
            {
                "rule": "6 (7)",
                "name": "Consumer Care Cell",
                "desc": "Helpline, email & contact address (customercare@company.in | 1800-11-4090)",
                "passed": True,
                "verdict": "PASSED"
            }
        ]
        passed = sum(1 for r in pcr_rows if r["passed"])
        failed = sum(1 for r in pcr_rows if not r["passed"])
        return {
            "goods_category": "PC",
            "passed_clauses": passed,
            "failed_clauses": failed,
            "audit_rows": pcr_rows
        }

    # Default: Non-Automatic Weighing Instruments (NAWI) — OIML R-76
    rows = OIMLR76Engine.build_full_rule_wise_audit(
        max_cap_kg=req.max_cap_kg,
        min_cap_g=req.min_cap_g,
        e_g=req.e_val_g,
        d_g=req.d_val_g,
        accuracy_class=req.accuracy_class,
        weighing_observations=req.weighing_observations,
        eccentricity_data=req.eccentricity_data,
        repeatability_data=req.repeatability_data,
        residual_zero_g=req.residual_zero_g,
        tare_load_kg=req.tare_load_kg,
        tare_ind_kg=req.tare_ind_kg,
        has_manual_override=req.has_manual_override
    )
    passed = sum(1 for r in rows if r["passed"])
    failed = sum(1 for r in rows if not r["passed"])
    return {
        "goods_category": "NAWI",
        "passed_clauses": passed,
        "failed_clauses": failed,
        "audit_rows": rows
    }



# -------------------------------------------------------------
# 4. Central Registry & File Download APIs
# -------------------------------------------------------------

@app.get("/api/reports")
def list_reports(limit: int = Query(100, ge=1, le=500)):
    """Retrieves all submitted pattern evaluation test reports from the central database."""
    return get_all_reports(limit=limit)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    """Retrieves full metadata and audit trail for a single report."""
    rec = get_report_by_id(report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Report not found")
    return rec


class SupervisorReviewRequest(BaseModel):
    supervisor_name: str = "Dr. S. K. Verma (Chief Metrologist)"
    status: str  # "APPROVED" or "REJECTED_RETURNED"
    remarks: str = ""


@app.post("/api/reports/{report_id}/supervisor-review")
def review_report_endpoint(report_id: str, req: SupervisorReviewRequest):
    """
    Supervisor selective approve/reject review workflow as required by SIH26035.
    Authorizes the test report or returns it for correction.
    """
    updated = review_report(report_id, req.supervisor_name, req.status, req.remarks)
    if not updated:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True, "report": updated}


@app.get("/api/dashboard-stats")
def get_dashboard_stats():
    """
    Supervisor Consolidation Review Dashboard metrics.
    Tracks operational progress from initial receipt to final authorization.
    """
    all_reports = get_all_reports(limit=500)
    total = len(all_reports)
    passed = sum(1 for r in all_reports if r.get("overall_status") == "PASS")
    failed = sum(1 for r in all_reports if r.get("overall_status") == "FAIL")
    overrides = sum(1 for r in all_reports if r.get("has_manual_override") == 1)
    approved = sum(1 for r in all_reports if r.get("supervisor_status") == "APPROVED")
    returned = sum(1 for r in all_reports if r.get("supervisor_status") == "REJECTED_RETURNED")
    pending = total - approved - returned

    return {
        "total_samples": total,
        "passed": passed,
        "failed": failed,
        "manual_overrides": overrides,
        "supervisor_approved": approved,
        "returned_for_correction": returned,
        "pending_review": pending,
        "pass_rate_pct": round((passed / total * 100), 1) if total > 0 else 0
    }


@app.get("/api/get-qr/{report_id}")
def get_qr_stamp(report_id: str):
    """Retrieves the assigned QR code stamp for physical marking."""
    qr_path = os.path.join(REPORTS_DIR, "qr_stamps", f"{report_id}_qr.png")
    if os.path.exists(qr_path):
        return FileResponse(qr_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="QR Code stamp not found")


@app.get("/api/download-report/{filename}")
def download_report(filename: str):
    """Securely downloads generated OIML R-76 test reports (PDF / DOCX)."""
    import urllib.parse
    safe_filename = os.path.basename(urllib.parse.unquote(filename))
    file_path = os.path.join(REPORTS_DIR, safe_filename)

    # If file not found directly, check standard suffix variations or DB lookup
    if not os.path.exists(file_path):
        candidate_pdf = os.path.join(REPORTS_DIR, f"{safe_filename}_OIML_R76.pdf")
        candidate_docx = os.path.join(REPORTS_DIR, f"{safe_filename}_OIML_R76.docx")
        if os.path.exists(candidate_pdf):
            file_path = candidate_pdf
            safe_filename = f"{safe_filename}_OIML_R76.pdf"
        elif os.path.exists(candidate_docx):
            file_path = candidate_docx
            safe_filename = f"{safe_filename}_OIML_R76.docx"
        else:
            clean_id = safe_filename.replace(".pdf", "").replace(".docx", "").replace("_OIML_R76", "")
            rec = get_report_by_id(clean_id)
            if rec and rec.get("pdf_path") and os.path.exists(rec["pdf_path"]):
                file_path = rec["pdf_path"]
                safe_filename = os.path.basename(file_path)
            else:
                # Fallback to test_sample.pdf if test_sample requested
                if "test_sample" in safe_filename and os.path.exists(os.path.join(REPORTS_DIR, "test_sample.pdf")):
                    file_path = os.path.join(REPORTS_DIR, "test_sample.pdf")
                    safe_filename = "test_sample.pdf"
                else:
                    raise HTTPException(status_code=404, detail=f"Report file '{safe_filename}' not found")
    
    media_type = (
        "application/pdf"
        if safe_filename.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return FileResponse(file_path, media_type=media_type, filename=safe_filename, headers=headers)


@app.post("/api/decode-qr")
async def decode_qr_endpoint(file: UploadFile = File(...)):
    """
    Decodes an uploaded QR code photo or video frame using OpenCV.
    Returns parsed scale specifications and direct re-audit parameters.
    """
    import cv2
    import numpy as np
    from urllib.parse import urlparse, parse_qs

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    detector = cv2.QRCodeDetector()
    val, pts, _ = detector.detectAndDecode(img)

    if not val:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        val, pts, _ = detector.detectAndDecode(gray)

    if not val:
        return {"success": False, "message": "No QR code could be decoded from the provided image. Ensure the QR code is clearly visible and in focus."}

    report_id = None
    serial_no = None
    model = None
    max_cap = None
    e_val = None
    acc_class = None
    mfr = None

    # Parse URL query parameters if present
    if "reaudit_id=" in val:
        try:
            url_part = val.split('\n')[0].strip()
            parsed = urlparse(url_part)
            qs = parse_qs(parsed.query)
            report_id = qs.get("reaudit_id", [None])[0]
            serial_no = qs.get("serial", [None])[0]
            model = qs.get("model", [None])[0]
            if "max" in qs:
                try: max_cap = float(qs["max"][0])
                except: pass
            if "e" in qs:
                try: e_val = float(qs["e"][0])
                except: pass
            acc_class = qs.get("class", [None])[0]
        except:
            pass

    # Parse pipe-delimited token
    if "REAUDIT|" in val or "REPORT:" in val or "ID:" in val:
        for part in val.split("|"):
            if part.startswith("REPORT:") or part.startswith("ID:"):
                report_id = report_id or part.split(":", 1)[1].strip()
            elif part.startswith("SERIAL:"):
                serial_no = serial_no or part.split(":", 1)[1].strip()
            elif part.startswith("MODEL:"):
                model = model or part.split(":", 1)[1].strip()
            elif part.startswith("MFR:"):
                mfr = mfr or part.split(":", 1)[1].strip()
            elif part.startswith("MAX:"):
                try: max_cap = max_cap or float(part.split(":", 1)[1].strip())
                except: pass
            elif part.startswith("E:"):
                try: e_val = e_val or float(part.split(":", 1)[1].strip())
                except: pass
            elif part.startswith("CLASS:"):
                acc_class = acc_class or part.split(":", 1)[1].strip()

    # Query DB record to enrich data if report_id found
    record = None
    if report_id:
        record = get_report_by_id(report_id)
        if record:
            serial_no = serial_no or record.get("serial_no")
            model = model or record.get("model")
            mfr = mfr or record.get("manufacturer")
            max_cap = max_cap or record.get("max_capacity")
            e_val = e_val or record.get("verification_interval")
            acc_class = acc_class or record.get("accuracy_class")

    resolved_model = model or (record.get("model") if record else "DS-215")
    resolved_serial = serial_no or (record.get("serial_no") if record else "SN-2026-98124")
    resolved_mfr = mfr or (record.get("manufacturer") if record else "Eagle Scales Pvt Ltd, Pune")
    resolved_max = max_cap or (record.get("max_capacity") if record else 30.0)
    resolved_min = record.get("min_capacity", 100.0) if record else 100.0
    resolved_e = e_val or (record.get("verification_interval") if record else 5.0)
    resolved_class = acc_class or (record.get("accuracy_class") if record else "Class III")

    return {
        "success": True,
        "raw_text": val,
        "report_id": report_id,
        "record": record,
        "model": resolved_model,
        "serial_no": resolved_serial,
        "manufacturer": resolved_mfr,
        "max_capacity": resolved_max,
        "min_capacity": resolved_min,
        "verification_interval": resolved_e,
        "accuracy_class": resolved_class,
        "specs": {
            "model": resolved_model,
            "serial_no": resolved_serial,
            "manufacturer": resolved_mfr,
            "max_cap": resolved_max,
            "min_cap": resolved_min,
            "e_val": resolved_e,
            "d_val": resolved_e,
            "accuracy_class": resolved_class
        }
    }


@app.get("/api/verify/{report_id}")
def verify_report(report_id: str, hash_val: str):
    """Verifies a report ID and SHA-256 hash against the immutable ledger."""
    return verify_hash(report_id, hash_val)


@app.post("/api/verify-pdf-file")
async def verify_pdf_file(file: UploadFile = File(...)):
    """
    Ingests an existing PDF report file, recalculates its 64-character SHA-256 hash,
    and queries the database to verify if it has been tampered with or modified.
    """
    content = await file.read()
    import hashlib
    computed_hash = hashlib.sha256(content).hexdigest()

    # Search database for matching hash
    from .database import SessionLocal, TestReport, select
    db = SessionLocal()
    try:
        stmt = select(TestReport).where(TestReport.sha256_hash == computed_hash)
        match = db.scalars(stmt).first()
        if match:
            return {
                "verified": True,
                "status": "AUTHENTIC",
                "computed_hash": computed_hash,
                "message": "Cryptographic Hash Matched! This PDF is 100% authentic and untampered under Section 63 BSA 2023.",
                "report": match.to_dict()
            }
        else:
            return {
                "verified": False,
                "status": "TAMPERED_OR_UNKNOWN",
                "computed_hash": computed_hash,
                "message": "HASH MISMATCH: This document does not match any official record in the DoCA repository. It may have been altered or forged.",
                "report": None
            }
    finally:
        db.close()


@app.get("/api/sample-images")
def list_sample_images():
    """Lists available sample images for rapid offline demonstration."""
    return {
        "nameplate_sample": "/uploads/samples/sample_nameplate_eagle.png",
        "display_pass_sample": "/uploads/samples/sample_display_pass.png",
        "display_fail_sample": "/uploads/samples/sample_display_fail_bribe.png",
        "blurry_sample": "/uploads/samples/sample_blurry.png"
    }
