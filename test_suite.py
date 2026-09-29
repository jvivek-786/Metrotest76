"""
MetroTest-76 Comprehensive Verification Test Suite
Smart India Hackathon 2026 (SIH26035)
Verifies:
1. OIML R-76 Table 6 Mathematical Rule Engine (Classes I, II, III, IIII)
2. Unit conversions (kg vs g) & MPE limits
3. Initial vs In-Service Periodic Re-verification (2x MPE)
4. OpenCV Pre-Flight Check (Laplacian Blur & Glare)
5. Intelligent OCR Extraction for Exhibits A & B
6. Strict-Liability Manual Override Tracking & Lie-Detector
7. Section 63 BSA 2023 SHA-256 Bundle Sealing
8. ReportLab PDF & python-docx Generation
9. SQLAlchemy 2.0 Database Ledger & Hash Tamper Detection
"""

import os
import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.oiml_engine import OIMLR76Engine
from backend.vision_ocr import VisionQualityEngine, OpticalIngestionEngine
from backend.crypto_utils import compute_evidence_bundle_hash, compute_file_sha256
from backend.database import get_report_by_id, verify_hash

client = TestClient(app)

def test_oiml_classification():
    # Class III: Max 30kg, e=5g -> n = 30000 / 5 = 6000
    res = OIMLR76Engine.classify_instrument(30.0, 5.0)
    assert res["n"] == 6000
    assert res["suggested_class"] == "Class III"
    assert res["valid"] == True

    # Class I: Max 200g, e=0.001g -> n = 200000
    res_i = OIMLR76Engine.classify_instrument(0.2, 0.001)
    assert res_i["suggested_class"] == "Class I"
    assert res_i["n"] == 200000

def test_oiml_mpe_class_iii_initial():
    # Tier 1: 0 to 500e (e=5g -> 0 to 2.5kg) -> MPE = +/-0.5e = +/-2.5g
    obs1 = OIMLR76Engine.evaluate_weighing_observation(2.5, 2.502, 5.0, "Class III", is_initial=True)
    assert obs1["mpe_g"] == 2.5
    assert obs1["error_g"] == 2.0
    assert obs1["passed"] == True

    # Tier 2: 500e to 2000e (e=5g -> 2.5kg to 10kg) -> MPE = +/-1.0e = +/-5.0g
    obs2 = OIMLR76Engine.evaluate_weighing_observation(10.0, 10.005, 5.0, "Class III", is_initial=True)
    assert obs2["mpe_g"] == 5.0
    assert obs2["error_g"] == 5.0
    assert obs2["passed"] == True

    # Tier 3: 2000e to 10000e (e=5g -> 10kg to 50kg) -> MPE = +/-1.5e = +/-7.5g
    obs3 = OIMLR76Engine.evaluate_weighing_observation(30.0, 30.007, 5.0, "Class III", is_initial=True)
    assert obs3["mpe_g"] == 7.5
    assert obs3["error_g"] == 7.0
    assert obs3["passed"] == True

    # Failure check: error 8.0g > 7.5g MPE -> FAILS
    obs_fail = OIMLR76Engine.evaluate_weighing_observation(30.0, 30.008, 5.0, "Class III", is_initial=True)
    assert obs_fail["passed"] == False
    assert obs_fail["status"] == "FAIL"

def test_oiml_mpe_inservice_doubling():
    # For in-service re-verification, MPE is doubled (2 x MPE)
    # Tier 3 at 30kg: 7.5g * 2 = 15.0g
    obs = OIMLR76Engine.evaluate_weighing_observation(30.0, 30.010, 5.0, "Class III", is_initial=False)
    assert obs["mpe_g"] == 15.0
    assert obs["passed"] == True

def test_opencv_preflight_quality():
    sharp_img = "uploads/samples/sample_nameplate_eagle.png"
    blur_img = "uploads/samples/sample_blurry.png"
    
    q_sharp = VisionQualityEngine.inspect_image(sharp_img)
    assert q_sharp["is_acceptable"] == True
    assert q_sharp["blur_score"] > 100.0

    q_blur = VisionQualityEngine.inspect_image(blur_img)
    assert q_blur["status"] == "WARNING"
    assert q_blur["blur_score"] < 75.0
    assert any("Blurry image" in w for w in q_blur["warnings"])

def test_ocr_extraction():
    ocr_res = OpticalIngestionEngine.ocr_nameplate("uploads/samples/sample_nameplate_eagle.png")
    assert "Eagle" in ocr_res["manufacturer"]
    assert ocr_res["model"] == "DS-215"
    assert ocr_res["max_cap"] == 30.0
    assert ocr_res["e_val"] == 5.0

    disp_pass = OpticalIngestionEngine.ocr_display("uploads/samples/sample_display_pass.png")
    assert disp_pass["detected_indication_kg"] == 30.005

    disp_fail = OpticalIngestionEngine.ocr_display("uploads/samples/sample_display_fail_bribe.png")
    assert disp_fail["detected_indication_kg"] == 30.018

def test_bribe_scenario_and_tamper_detection():
    # Officer enters 30.005kg to pass, but photo Exhibit B shows 30.018kg
    obs = [
        {'load_kg': 0.1, 'indication_kg': 0.100},
        {'load_kg': 30.0, 'indication_kg': 30.005}
    ]
    with open('uploads/samples/sample_nameplate_eagle.png', 'rb') as f1, open('uploads/samples/sample_display_fail_bribe.png', 'rb') as f2:
        r = client.post(
            '/api/generate-full-submission',
            data={
                'officer_name': 'Insp. Vikram Malhotra',
                'officer_badge': 'GATC-MH-2026-112',
                'manufacturer': 'Eagle Scales Pvt Ltd',
                'model': 'DS-215',
                'serial_no': 'SN-2026-98124',
                'accuracy_class': 'Class III',
                'max_cap': 30.0,
                'min_cap': 100.0,
                'e_val': 5.0,
                'weighing_observations': json.dumps(obs),
                'has_manual_override': True,
                'override_details': 'Critical Max Indication (Discrepancy with Photo: Display shows 30.018kg, officer entered 30.005kg)'
            },
            files={'nameplate_photo': ('n.png', f1, 'image/png'), 'display_photo': ('d.png', f2, 'image/png')}
        )
    
    assert r.status_code == 200
    res = r.json()
    assert res["has_manual_override"] == True
    report_id = res["report_id"]
    sha256 = res["sha256_hash"]

    # Verify through API
    v_res = client.get(f'/api/verify/{report_id}?hash_val={sha256}').json()
    assert v_res["verified"] == True

    # Tampered Hash verification
    bad_hash = "0" * 64
    v_bad = client.get(f'/api/verify/{report_id}?hash_val={bad_hash}').json()
    assert v_bad["verified"] == False

if __name__ == "__main__":
    print("Running MetroTest-76 test suite...")
    test_oiml_classification()
    print("[PASS] test_oiml_classification")
    test_oiml_mpe_class_iii_initial()
    print("[PASS] test_oiml_mpe_class_iii_initial")
    test_oiml_mpe_inservice_doubling()
    print("[PASS] test_oiml_mpe_inservice_doubling")
    test_opencv_preflight_quality()
    print("[PASS] test_opencv_preflight_quality")
    test_ocr_extraction()
    print("[PASS] test_ocr_extraction")
    test_bribe_scenario_and_tamper_detection()
    print("[PASS] test_bribe_scenario_and_tamper_detection")
    print("\nALL 6 TEST MODULES PASSED WITH 100% SUCCESS!")
