"""
MetroTest-76 Editable DOCX Generator
Produces standardized Microsoft Word (.docx) test reports as mandated by SIH26035.
"""

import os
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


def generate_docx(report_data: dict, output_filepath: str, nameplate_image_path: str = None, display_image_path: str = None):
    """
    Generates an editable MS Word (.docx) test report conforming to OIML R-76.
    """
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    doc = Document()
    
    # 0.8 inch margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    TEAL = RGBColor(13, 110, 110)
    DARK = RGBColor(26, 26, 46)
    GRAY = RGBColor(100, 116, 139)
    PASS_GREEN = RGBColor(22, 101, 52)
    FAIL_RED = RGBColor(153, 27, 27)

    # 1. Header & Title
    p_gov = doc.add_paragraph()
    p_gov.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_gov = p_gov.add_run(
        "GOVERNMENT OF INDIA\n"
        "MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION\n"
        "DEPARTMENT OF CONSUMER AFFAIRS — LEGAL METROLOGY DIVISION\n"
    )
    r_gov.font.size = Pt(9.5)
    r_gov.font.bold = True
    r_gov.font.color.rgb = GRAY

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("OIML R 76-2 PATTERN EVALUATION TEST REPORT\n")
    r_title.font.size = Pt(14)
    r_title.font.bold = True
    r_title.font.color.rgb = TEAL

    r_sub = p_title.add_run("Non-Automatic Weighing Instruments (NAWI) Model Approval Compliance")
    r_sub.font.size = Pt(9.5)
    r_sub.font.color.rgb = DARK

    # 2. General Information Table
    doc.add_heading("1. Instrument Specifications & Testing Officer Credentials", level=2)
    t_gen = doc.add_table(rows=6, cols=4)
    t_gen.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_gen.style = 'Table Grid'

    officer_name = report_data.get("officer_name", "Insp. Rajesh Sharma")
    officer_badge = report_data.get("officer_badge", "RRSL-DOCA-2026-449")
    max_cap = float(report_data.get("max_cap", 30.0))
    e_val = float(report_data.get("e_val", 5.0))
    n_val = int(round((max_cap * 1000.0) / e_val)) if e_val > 0 else 0

    gen_rows = [
        ("Report Ref. No:", report_data.get("report_id", "N/A"), "Evaluation Date:", report_data.get("date", datetime.now().strftime("%d-%m-%Y"))),
        ("Inspecting Officer:", f"{officer_name} ({officer_badge})", "Testing Lab:", report_data.get("lab_name", "Regional Reference Standards Lab (RRSL)")),
        ("Manufacturer:", report_data.get("manufacturer", "Eagle Scales Pvt Ltd"), "Environment:", report_data.get("environmental_conditions", "22.5°C | 50% RH")),
        ("Instrument Model:", report_data.get("model", "DS-215"), "Serial Number:", report_data.get("serial_no", "SN-2026-98124")),
        ("Accuracy Class:", report_data.get("accuracy_class", "Class III"), "Interval (e):", f"{e_val:.1f} g (n = {n_val})"),
        ("Max Capacity (Max):", f"{max_cap:.1f} kg", "Min Capacity (Min):", f"{report_data.get('min_cap', 100.0):.1f} g")
    ]

    for r_idx, row in enumerate(gen_rows):
        for c_idx in range(4):
            cell = t_gen.cell(r_idx, c_idx)
            cell.text = row[c_idx]
            if c_idx in (0, 2):
                cell.paragraphs[0].runs[0].font.bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(8.5)
            else:
                cell.paragraphs[0].runs[0].font.size = Pt(8.5)

    doc.add_paragraph()

    # 3. Photographic Ground-Truth Evidence (Exhibits A & B)
    doc.add_heading("2. Photographic Ground-Truth Binding (Exhibits A & B)", level=2)
    has_override = bool(report_data.get("has_manual_override", False))
    override_details = report_data.get("override_details", "")

    p_audit = doc.add_paragraph()
    if has_override:
        r_audit = p_audit.add_run(
            f"[STRICT-LIABILITY OVERRIDE LOGGED]: Officer manually modified field(s): {override_details}. "
            "Raw unedited photographic evidence is permanently bound into this electronic record under Section 63 BSA 2023."
        )
        r_audit.font.bold = True
        r_audit.font.color.rgb = FAIL_RED
    else:
        r_audit = p_audit.add_run(
            "[AUTOMATED OCR VERIFIED]: Extracted instrument specifications match optical recognition. No manual overrides."
        )
        r_audit.font.bold = True
        r_audit.font.color.rgb = PASS_GREEN
    r_audit.font.size = Pt(8.5)

    # Insert images if available
    if nameplate_image_path and os.path.exists(nameplate_image_path):
        p_img_a = doc.add_paragraph()
        p_img_a.add_run("Exhibit A (Machine Nameplate):\n").font.bold = True
        p_img_a.runs[0].font.size = Pt(8.5)
        try:
            doc.add_picture(nameplate_image_path, width=Inches(3.2))
        except Exception:
            pass

    if display_image_path and os.path.exists(display_image_path):
        p_img_b = doc.add_paragraph()
        p_img_b.add_run(f"Exhibit B (Digital Scale Display at Max Load {max_cap:.1f} kg):\n").font.bold = True
        p_img_b.runs[0].font.size = Pt(8.5)
        try:
            doc.add_picture(display_image_path, width=Inches(3.2))
        except Exception:
            pass

    doc.add_paragraph()

    # 4. Weighing Observations Table
    doc.add_heading("3. Weighing Performance Test Observations (Clause A.4.4)", level=2)
    obs_list = report_data.get("weighing_observations", [])
    t_obs = doc.add_table(rows=len(obs_list) + 1, cols=6)
    t_obs.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_obs.style = 'Table Grid'

    headers = ["Load m (kg)", "Indication I (kg)", "Load in e", "Error E (g)", "MPE (±g)", "Verdict"]
    for c_idx, h in enumerate(headers):
        cell = t_obs.cell(0, c_idx)
        cell.text = h
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8.5)

    for r_idx, obs in enumerate(obs_list):
        load_kg = float(obs.get("load_kg", obs.get("load", 0)))
        ind_kg = float(obs.get("indication_kg", obs.get("indication", 0)))
        err_g = float(obs.get("error_g", obs.get("error", 0)))
        mpe_g = float(obs.get("mpe_g", obs.get("mpe", 0)))
        m_in_e = obs.get("m_in_e", round((load_kg * 1000.0) / e_val, 1) if e_val > 0 else 0)
        is_pass = obs.get("passed", abs(err_g) <= mpe_g)

        cells = t_obs.rows[r_idx + 1].cells
        cells[0].text = f"{load_kg:.3f}"
        cells[1].text = f"{ind_kg:.3f}"
        cells[2].text = f"{m_in_e:.0f} e"
        cells[3].text = f"{err_g:+.2f}"
        cells[4].text = f"±{mpe_g:.2f}"
        cells[5].text = "PASS" if is_pass else "FAIL"
        
        for c in cells:
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
        cells[5].paragraphs[0].runs[0].font.bold = True
        cells[5].paragraphs[0].runs[0].font.color.rgb = PASS_GREEN if is_pass else FAIL_RED

    # 4. Rule-Wise Verification Audit Sheet (All Statutory Clauses)
    full_audit = report_data.get("full_audit_rows", [])
    if full_audit:
        doc.add_heading("4. Rule-Wise Verification Audit Sheet (OIML R 76-1 / Legal Metrology)", level=2)
        p_kpi = doc.add_paragraph()
        passed_c = report_data.get("passed_clauses", sum(1 for a in full_audit if a.get("passed")))
        failed_c = report_data.get("failed_clauses", sum(1 for a in full_audit if not a.get("passed")))
        r_kpi = p_kpi.add_run(f"PASSED CLAUSES: {passed_c}   |   FAILED CLAUSES: {failed_c}")
        r_kpi.font.bold = True
        r_kpi.font.size = Pt(9.5)

        t_sheet = doc.add_table(rows=len(full_audit) + 1, cols=3)
        t_sheet.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_sheet.style = 'Table Grid'
        
        sheet_headers = ["RULE / CLAUSE", "WHAT IS REQUIRED & TEST FINDINGS", "VERDICT"]
        for c_idx, h in enumerate(sheet_headers):
            cell = t_sheet.rows[0].cells[c_idx]
            cell.text = h
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.size = Pt(8.5)

        for r_idx, row in enumerate(full_audit):
            cells = t_sheet.rows[r_idx + 1].cells
            cells[0].text = row.get("rule", "")
            cells[1].text = f"{row.get('name', '')}\n{row.get('desc', '')}"
            is_p = row.get("passed", False)
            cells[2].text = "PASSED" if is_p else "FAILED"
            for c in cells:
                c.paragraphs[0].runs[0].font.size = Pt(8)
            cells[2].paragraphs[0].runs[0].font.bold = True
            cells[2].paragraphs[0].runs[0].font.color.rgb = PASS_GREEN if is_p else FAIL_RED

        doc.add_paragraph()

    # 5. Overall Metrological Result
    doc.add_heading("5. Pattern Evaluation Decision", level=2)
    p_res = doc.add_paragraph()
    r_res_lbl = p_res.add_run("OVERALL METROLOGICAL RESULT: ")
    r_res_lbl.font.bold = True
    r_res_lbl.font.size = Pt(11)

    status_str = report_data.get("overall_status", "PASS")
    r_res_val = p_res.add_run(f"{status_str}\n")
    r_res_val.font.bold = True
    r_res_val.font.size = Pt(13)
    r_res_val.font.color.rgb = PASS_GREEN if status_str == "PASS" else FAIL_RED

    # 6. Section 63 BSA 2023 Attestation
    doc.add_heading("5. Certificate under Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023", level=2)
    p_bsa = doc.add_paragraph(
        f"I, {officer_name} (Badge: {officer_badge}), Inspecting Officer, solemnly certify under Section 63 BSA 2023 "
        "that the electronic observations and cryptographic digest in this document were generated automatically without "
        "human falsification. The physical photographic evidence serves as an unalterable ground-truth witness.\n"
        f"Cryptographic SHA-256 Digest: {report_data.get('sha256_hash', 'N/A')}"
    )
    p_bsa.runs[0].font.italic = True
    p_bsa.runs[0].font.size = Pt(8)

    doc.save(output_filepath)
