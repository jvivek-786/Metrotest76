"""
MetroTest-76 Official PDF Report Generator
Generates tamper-evident OIML R 76-2 Pattern Evaluation Reports
with embedded photographic ground truth (Exhibits A & B),
cryptographic SHA-256 evidence sealing, and Section 63 BSA 2023 attestation.
"""

import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether
)

from .crypto_utils import generate_qr_verification_badge, compute_file_sha256, compute_evidence_bundle_hash


class OIMLReportGenerator:

    @classmethod
    def generate_pdf(
        cls,
        report_data: Dict[str, Any],
        output_filepath: str,
        nameplate_image_path: Optional[str] = None,
        display_image_path: Optional[str] = None
    ) -> str:
        """
        Builds the official OIML R 76-2 Test Report PDF with ReportLab.
        Returns the final SHA-256 hash of the generated PDF.
        """
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        qr_dir = os.path.join(os.path.dirname(output_filepath), "qr_stamps")
        os.makedirs(qr_dir, exist_ok=True)

        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=A4,
            leftMargin=1.2 * cm,
            rightMargin=1.2 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm
        )

        styles = getSampleStyleSheet()

        TEAL = colors.HexColor("#0d6e6e")
        DARK = colors.HexColor("#1a1a2e")
        GOLD = colors.HexColor("#f0a500")
        LGRAY = colors.HexColor("#f8fafc")
        BORDER_GRAY = colors.HexColor("#cbd5e1")
        PASS_GREEN = colors.HexColor("#166534")
        FAIL_RED = colors.HexColor("#991b1b")
        PASS_BG = colors.HexColor("#dcfce7")
        FAIL_BG = colors.HexColor("#fee2e2")

        title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=13, textColor=TEAL, fontName="Helvetica-Bold", leading=15, spaceAfter=2)
        gov_style = ParagraphStyle("GovStyle", parent=styles["Normal"], fontSize=8, textColor=DARK, fontName="Helvetica-Bold", alignment=1, leading=10)
        sub_style = ParagraphStyle("SubStyle", parent=styles["Normal"], fontSize=8, textColor=DARK, fontName="Helvetica", alignment=1, spaceAfter=2)
        h2_style = ParagraphStyle("H2Style", parent=styles["Heading2"], fontSize=9, textColor=TEAL, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=3)
        body_style = ParagraphStyle("BodyStyle", parent=styles["Normal"], fontSize=7, textColor=DARK, fontName="Helvetica", leading=9)
        alert_style = ParagraphStyle("AlertStyle", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Bold", leading=9)

        story = []

        # ---------------------------------------------------------
        # 1. Official Header & Government Branding
        # ---------------------------------------------------------
        story.append(Paragraph("GOVERNMENT OF INDIA", gov_style))
        story.append(Paragraph("MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION", gov_style))
        story.append(Paragraph("DEPARTMENT OF CONSUMER AFFAIRS — LEGAL METROLOGY DIVISION", gov_style))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph("OIML R 76-2 PATTERN EVALUATION TEST REPORT", title_style))
        story.append(Paragraph("Non-Automatic Weighing Instruments (NAWI) Model Approval Compliance", sub_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=4))

        # ---------------------------------------------------------
        # 2. General Information & Officer Credentials
        # ---------------------------------------------------------
        report_id = report_data.get("report_id", "TR-2026-UNKNOWN")
        officer_name = report_data.get("officer_name", "Insp. Rajesh Sharma")
        officer_badge = report_data.get("officer_badge", "RRSL-DOCA-2026-449")
        overall_status = report_data.get("overall_status", "PASS")
        has_override = bool(report_data.get("has_manual_override", False))
        override_details = report_data.get("override_details", "")
        max_cap = float(report_data.get("max_cap", 30.0))
        e_val = float(report_data.get("e_val", 5.0))
        n_intervals = int(round((max_cap * 1000.0) / e_val)) if e_val > 0 else 0

        eval_date = report_data.get("date", datetime.now().strftime("%d-%m-%Y %H:%M:%S UTC"))
        gps_loc = report_data.get("gps_coordinates", "18.5204° N, 73.8567° E (RRSL Pune)")
        env_cond = report_data.get("environmental_conditions", "22.5°C | 50% RH")
        model = report_data.get("model", "DS-215")
        serial_no = report_data.get("serial_no", "SN-2026-98124")
        manufacturer = report_data.get("manufacturer", "Eagle Scales Pvt Ltd")
        acc_class = report_data.get("accuracy_class", "Class III")

        gen_data = [
            ["Report Ref. No:", report_id, "Evaluation Date:", eval_date],
            ["Inspecting Officer:", f"{officer_name} ({officer_badge})", "Testing Laboratory:", report_data.get("lab_name", "Regional Reference Standards Lab (RRSL)")],
            ["Manufacturer Name:", report_data.get("manufacturer", "Eagle Scales Pvt Ltd"), "Operating Environment:", env_cond],
            ["Instrument Model:", report_data.get("model", "DS-215"), "Serial Number:", report_data.get("serial_no", "SN-2026-98124")],
            ["Accuracy Class:", report_data.get("accuracy_class", "Class III"), "Verification Interval (e):", f"{e_val:.1f} g (n = {n_intervals})"],
            ["Max Capacity (Max):", f"{max_cap:.1f} kg", "Min Capacity (Min):", f"{report_data.get('min_cap', 100.0):.1f} g"]
        ]
        t_gen = Table(gen_data, colWidths=[3.8 * cm, 5.5 * cm, 3.8 * cm, 5.5 * cm])
        t_gen.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), LGRAY),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
            ('TOPPADDING', (0,0), (-1,-1), 1.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
        ]))
        story.append(t_gen)
        story.append(Spacer(1, 0.1 * cm))

        # ---------------------------------------------------------
        # 3. Non-Repudiation through Photographic Ground-Truth Binding
        # (Exhibit A: Nameplate & Exhibit B: Digital Display at Max Load)
        # ---------------------------------------------------------
        story.append(Paragraph("PHOTOGRAPHIC GROUND-TRUTH EVIDENCE (SECTION 63 BSA 2023 BINDING)", h2_style))

        exhibit_cells = []
        has_a = nameplate_image_path and os.path.exists(nameplate_image_path)
        has_b = display_image_path and os.path.exists(display_image_path)

        # Exhibit A Cell
        if has_a:
            img_a = Image(nameplate_image_path, width=8.5 * cm, height=3.3 * cm)
            caption_a = Paragraph("<b>EXHIBIT A:</b> Machine Rating Plate (Riveted Identity Plate)", body_style)
            cell_a = [img_a, Spacer(1, 1), caption_a]
        else:
            cell_a = [Paragraph("<b>EXHIBIT A:</b> Rating Plate (Digital Record Only)", body_style)]

        # Exhibit B Cell
        if has_b:
            img_b = Image(display_image_path, width=8.5 * cm, height=3.3 * cm)
            caption_b = Paragraph(f"<b>EXHIBIT B:</b> Digital Scale Display at Max Load ({max_cap:.1f} kg)", body_style)
            cell_b = [img_b, Spacer(1, 1), caption_b]
        else:
            cell_b = [Paragraph("<b>EXHIBIT B:</b> Digital Display at Max Load (Not Attached)", body_style)]

        t_exhibits = Table([[cell_a, cell_b]], colWidths=[9.3 * cm, 9.3 * cm])
        t_exhibits.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), LGRAY),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_exhibits)
        story.append(Spacer(1, 0.1 * cm))

        # Strict Liability Audit Banner
        if has_override:
            override_text = (
                "<font color='#991b1b'><b>[STRICT-LIABILITY MANUAL OVERRIDE LOGGED]:</b> "
                f"Officer manually modified field(s): <b>{override_details}</b>. "
                "Raw unedited photographic evidence above has been permanently bound into this certificate under Section 63 BSA 2023. "
                "Discrepancies between physical photos and claimed readings are subject to criminal liability under Bharatiya Nyaya Sanhita (BNS) 2023.</font>"
            )
            banner_bg = FAIL_BG
            banner_border = FAIL_RED
        else:
            override_text = (
                "<font color='#166534'><b>[AUTOMATED OCR VERIFIED]:</b> "
                "Extracted instrument specifications and digital display values match optical recognition. "
                "Raw photographic pixels cryptographically sealed without manual override.</font>"
            )
            banner_bg = PASS_BG
            banner_border = PASS_GREEN

        t_audit_banner = Table([[Paragraph(override_text, alert_style)]], colWidths=[18.6 * cm])
        t_audit_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), banner_bg),
            ('BOX', (0,0), (-1,-1), 1, banner_border),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_audit_banner)
        story.append(Spacer(1, 0.1 * cm))

        # ---------------------------------------------------------
        # 4. Weighing Performance Test Observations (Clause A.4.4)
        # ---------------------------------------------------------
        story.append(Paragraph("1. WEIGHING PERFORMANCE TEST OBSERVATIONS (OIML R 76-1 Clause A.4.4)", h2_style))
        obs_header = ["Load m (kg)", "Indication I (kg)", "Load in e", "Error E (g)", "Statutory MPE (±g)", "Verdict"]
        obs_rows = [obs_header]

        for obs in report_data.get("weighing_observations", []):
            load_kg = float(obs.get("load_kg", obs.get("load", 0)))
            ind_kg = float(obs.get("indication_kg", obs.get("indication", 0)))
            err_g = float(obs.get("error_g", obs.get("error", (ind_kg - load_kg) * 1000.0)))
            mpe_g = float(obs.get("mpe_g", obs.get("mpe", 0)))
            m_in_e = obs.get("m_in_e", round((load_kg * 1000.0) / e_val, 1) if e_val > 0 else 0)
            is_pass = obs.get("passed", abs(err_g) <= mpe_g)

            verdict_text = f"<font color='{'#166534' if is_pass else '#991b1b'}'><b>{'PASS' if is_pass else 'FAIL'}</b></font>"
            obs_rows.append([
                f"{load_kg:.3f}",
                f"{ind_kg:.3f}",
                f"{m_in_e:.0f} e",
                f"{err_g:+.2f}",
                f"±{mpe_g:.2f}",
                Paragraph(verdict_text, body_style)
            ])

        t_obs = Table(obs_rows, colWidths=[3.1 * cm, 3.1 * cm, 2.8 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm])
        t_obs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), TEAL),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
            ('TOPPADDING', (0,0), (-1,-1), 1.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
        ]))
        story.append(t_obs)
        story.append(Spacer(1, 0.1 * cm))

        # ---------------------------------------------------------
        # 5. Rule-Wise Verification Audit Sheet (All Statutory Clauses)
        # ---------------------------------------------------------
        full_audit = report_data.get("full_audit_rows", [])
        if full_audit:
            passed_c = report_data.get("passed_clauses", sum(1 for a in full_audit if a.get("passed")))
            failed_c = report_data.get("failed_clauses", sum(1 for a in full_audit if not a.get("passed")))
            
            # KPI score banner
            kpi_p = Paragraph(f"<b>PASSED CLAUSES: <font color='#166534'>{passed_c}</font></b> &nbsp;&nbsp;|&nbsp;&nbsp; <b>FAILED CLAUSES: <font color='#991b1b'>{failed_c}</font></b>", alert_style)
            t_kpi = Table([[kpi_p]], colWidths=[18.6 * cm])
            t_kpi.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), LGRAY),
                ('BOX', (0,0), (-1,-1), 0.5, BORDER_GRAY),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(Spacer(1, 0.1 * cm))
            story.append(Paragraph("2. RULE-WISE VERIFICATION AUDIT SHEET (OIML R 76-1 / LEGAL METROLOGY ASSESSMENT)", h2_style))
            story.append(t_kpi)
            story.append(Spacer(1, 0.1 * cm))

            audit_table_data = [["RULE / CLAUSE", "WHAT IS REQUIRED & TEST FINDINGS", "VERDICT"]]
            for row in full_audit:
                is_p = row.get("passed", False)
                v_html = f"<font color='{'#166534' if is_p else '#991b1b'}'><b>{'✓ PASSED' if is_p else '✕ FAILED'}</b></font>"
                desc_html = f"<b>{row.get('name', '')}</b><br/>{row.get('desc', '')}"
                audit_table_data.append([
                    Paragraph(f"<b>{row.get('rule', '')}</b>", body_style),
                    Paragraph(desc_html, body_style),
                    Paragraph(v_html, body_style)
                ])

            t_audit_sheet = Table(audit_table_data, colWidths=[3.2 * cm, 12.6 * cm, 2.8 * cm])
            t_audit_sheet.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), TEAL),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('ALIGN', (2,0), (2,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTSIZE', (0,0), (-1,-1), 6.5),
                ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
                ('TOPPADDING', (0,0), (-1,-1), 1.5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
            ]))
            story.append(t_audit_sheet)
            story.append(Spacer(1, 0.1 * cm))


        # ---------------------------------------------------------
        # 6. Verdict Banner & Assigned QR Verification Stamp
        # ---------------------------------------------------------
        story.append(Paragraph("3. PATTERN EVALUATION DECISION & ASSIGNED QR BADGE", h2_style))

        qr_file = os.path.join(qr_dir, f"{report_id}_qr.png")
        # Pre-compute bundle hash
        evidence_hash = compute_evidence_bundle_hash(
            officer_badge=officer_badge,
            officer_name=officer_name,
            nameplate_photo_path=nameplate_image_path,
            display_photo_path=display_image_path,
            gps_coordinates=gps_loc,
            timestamp_iso=eval_date,
            weighing_observations=report_data.get("weighing_observations", []),
            verdict=overall_status,
            has_manual_override=has_override,
            override_details=override_details
        )

        generate_qr_verification_badge(
            report_id=report_id,
            sha256_hash=evidence_hash,
            verdict=overall_status,
            officer_badge=officer_badge,
            output_path=qr_file,
            model=model,
            serial_no=serial_no,
            max_cap=max_cap,
            e_val=e_val,
            acc_class=acc_class,
            mfr=manufacturer
        )

        qr_img = Image(qr_file, width=2.5 * cm, height=2.5 * cm)
        verdict_color_hex = "#166534" if overall_status == "PASS" else "#991b1b"
        verdict_box_bg = PASS_BG if overall_status == "PASS" else FAIL_BG

        verdict_text = (
            f"<font size=10 color='{verdict_color_hex}'><b>OVERALL STATUTORY DECISION: {overall_status}</b></font><br/>"
            f"<font size=7 color='#1a1a2e'>This weighing instrument has been evaluated in strict accordance with the Legal Metrology Act, 2009, "
            f"Legal Metrology (General) Rules, 2011, and OIML R 76-1/2 Table 6 MPE limits. "
            f"<b>DIRECT RE-AUDIT QR:</b> Scan the QR stamp on annual or surprise inspections to automatically authenticate machine specs and launch verification tests directly.</font>"
        )

        qr_cell = [
            qr_img,
            Paragraph("<div align='center'><font size=5.5 color='#0d6e6e'><b>SCAN TO RE-AUDIT</b></font></div>", body_style)
        ]
        t_verdict = Table([[Paragraph(verdict_text, body_style), qr_cell]], colWidths=[15.8 * cm, 2.8 * cm])
        t_verdict.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), verdict_box_bg),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor(verdict_color_hex)),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_verdict)
        story.append(Spacer(1, 0.1 * cm))

        # ---------------------------------------------------------
        # 7. Certificate under Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023
        # ---------------------------------------------------------
        story.append(Paragraph("4. CERTIFICATE UNDER SECTION 63 OF BHARATIYA SAKSHYA ADHINIYAM (BSA), 2023", h2_style))
        bsa_declaration = (
            f"<b>Officer Non-Repudiation Attestation:</b> I, {officer_name} (Badge: {officer_badge}), Inspecting Officer at "
            f"{report_data.get('lab_name', 'Regional Reference Standards Laboratory')}, solemnly declare under penalty of perjury "
            f"and Section 63 of Bharatiya Sakshya Adhiniyam, 2023, that this electronic record was produced during official testing "
            f"at coordinates [{gps_loc}]. The physical rating plate in Exhibit A and scale readout in Exhibit B represent "
            f"unaltered ground-truth observations bound into the cryptographic SHA-256 evidence digest below."
        )
        story.append(Paragraph(bsa_declaration, ParagraphStyle("BSADec", parent=body_style, fontSize=6.5, leading=8)))
        story.append(Spacer(1, 0.08 * cm))

        hash_table = [
            ["SHA-256 EVIDENCE DIGEST:", evidence_hash],
            ["ELECTRONIC SIGNATURE:", f"{officer_name} [{officer_badge}] | CENTRALLY REGISTERED DOCA COMPLIANCE STAMP"]
        ]
        t_hash = Table(hash_table, colWidths=[4.2 * cm, 14.4 * cm])
        t_hash.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), LGRAY),
            ('FONTNAME', (0,0), (-1,-1), 'Courier-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(t_hash)

        # Build document
        doc.build(story)

        # Compute final SHA-256 of the generated PDF file
        final_pdf_hash = compute_file_sha256(output_filepath)
        return final_pdf_hash
