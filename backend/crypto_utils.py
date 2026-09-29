"""
MetroTest-76 Cryptography & Legal Non-Repudiation Module
Implements Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023 Digital Sealing.
Binds Officer SSO Credentials, Raw Exhibit Photos, GPS Timestamps, and Metrological Readings.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import qrcode
from PIL import Image, ImageDraw, ImageFont


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hex digest of a binary file on disk."""
    if not filepath or not os.path.exists(filepath):
        return "0" * 64
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_evidence_bundle_hash(
    officer_badge: str,
    officer_name: str,
    nameplate_photo_path: Optional[str],
    display_photo_path: Optional[str],
    gps_coordinates: str,
    timestamp_iso: str,
    weighing_observations: list,
    verdict: str,
    has_manual_override: bool,
    override_details: str
) -> str:
    """
    Computes cryptographic SHA-256 digest over the entire canonical evidence bundle:
    [Officer_Badge + Exhibit_Photos + GPS_Timestamp + Table_of_Readings + Verdict]
    """
    nameplate_hash = compute_file_sha256(nameplate_photo_path) if nameplate_photo_path else "NO_EXHIBIT_A"
    display_hash = compute_file_sha256(display_photo_path) if display_photo_path else "NO_EXHIBIT_B"

    # Canonicalize observations to ensure deterministic hash regardless of formatting
    clean_obs = []
    for obs in weighing_observations:
        clean_obs.append({
            "load_kg": float(obs.get("load_kg", obs.get("load", 0))),
            "indication_kg": float(obs.get("indication_kg", obs.get("indication", 0))),
            "error_g": float(obs.get("error_g", obs.get("error", 0))),
            "mpe_g": float(obs.get("mpe_g", obs.get("mpe", 0))),
            "passed": bool(obs.get("passed", False))
        })

    bundle = {
        "bsa_section": "Section 63 Bharatiya Sakshya Adhiniyam 2023",
        "officer": {
            "name": officer_name.strip(),
            "badge": officer_badge.strip()
        },
        "exhibits": {
            "exhibit_a_nameplate_sha256": nameplate_hash,
            "exhibit_b_display_sha256": display_hash
        },
        "spatial_temporal": {
            "gps": gps_coordinates.strip() if gps_coordinates else "28.6139° N, 77.2090° E (RRSL)",
            "timestamp": timestamp_iso
        },
        "metrology_verdict": verdict,
        "observations": clean_obs,
        "override_audit": {
            "has_override": bool(has_manual_override),
            "details": override_details.strip()
        }
    }

    bundle_json = json.dumps(bundle, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(bundle_json.encode('utf-8')).hexdigest()


def generate_qr_verification_badge(
    report_id: str,
    sha256_hash: str,
    verdict: str,
    officer_badge: str,
    output_path: str,
    model: str = "",
    serial_no: str = "",
    max_cap: float = 30.0,
    e_val: float = 5.0,
    acc_class: str = "Class III",
    mfr: str = ""
):
    """
    Generates high-contrast PIL-based verification QR code.
    Encodes URL-ready payload, direct re-audit launcher, and central registry token.
    When scanned during annual/surprise inspections, launches directly into OIML R-76 test suite.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Direct Re-Audit URL + Pipe Token
    qr_payload = (
        f"http://127.0.0.1:8007/?reaudit_id={report_id}&serial={serial_no}&model={model}&max={max_cap}&e={e_val}&class={acc_class}\n"
        f"DOCA-OIML-R76-REAUDIT|REPORT:{report_id}|MFR:{mfr}|MODEL:{model}|SERIAL:{serial_no}|MAX:{max_cap}|E:{e_val}|CLASS:{acc_class}|STATUS:{verdict}|SHA256:{sha256_hash}"
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    # Use Government Dark Teal (#0d6e6e)
    img = qr.make_image(fill_color="#0d6e6e", back_color="white").convert("RGB")
    img.save(output_path)
    return output_path
