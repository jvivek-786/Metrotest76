"""
MetroTest-76 Database Module
SQLAlchemy 2.0 ORM implementation for SQLite (local offline operation)
with zero-code migration path to central PostgreSQL.
Statutory schema complies with Section 5 of SIH26035 specification.
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text,
    DateTime, Boolean, select, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_FILE = os.path.join(os.path.dirname(__file__), "metrotest76.db")

# Support central PostgreSQL or local SQLite seamlessly
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TestReport(Base):
    """
    Statutory OIML R-76 Test Report and Audit Ledger
    Conforms directly to SIH26035 Section 5 Database Specification.
    """
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), unique=True, nullable=False, index=True)
    officer_name = Column(String(128), nullable=False)
    officer_badge = Column(String(64), nullable=False)
    manufacturer = Column(String(128), nullable=False)
    model = Column(String(64), nullable=False)
    serial_no = Column(String(64), nullable=False)
    accuracy_class = Column(String(32), nullable=False)
    max_capacity = Column(Float, nullable=False)          # in kg
    min_capacity = Column(Float, nullable=False)          # in g
    verification_interval = Column(Float, nullable=False) # e in g
    environmental_conditions = Column(String(128), default="22.5°C | 50% RH")
    overall_status = Column(String(16), nullable=False)   # PASS or FAIL
    sha256_hash = Column(String(64), nullable=False)      # 64-character hex digest
    pdf_path = Column(String(256), nullable=False)
    docx_path = Column(String(256), nullable=False)
    nameplate_photo_path = Column(String(256), nullable=True)  # Exhibit A path
    display_photo_path = Column(String(256), nullable=True)    # Exhibit B path
    has_manual_override = Column(Integer, default=0)           # 1 if officer edited OCR
    override_details = Column(Text, nullable=True)             # Names/reasons of edited fields
    observations_json = Column(Text, nullable=True)            # Full test observations JSON
    eccentricity_json = Column(Text, nullable=True)            # Eccentricity test JSON
    repeatability_json = Column(Text, nullable=True)           # Repeatability test JSON
    supervisor_status = Column(String(32), default="PENDING_REVIEW") # PENDING_REVIEW, APPROVED, REJECTED_RETURNED
    supervisor_remarks = Column(Text, nullable=True)
    supervisor_name = Column(String(128), nullable=True)
    supervisor_signed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "officer_name": self.officer_name,
            "officer_badge": self.officer_badge,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_no": self.serial_no,
            "accuracy_class": self.accuracy_class,
            "max_capacity": self.max_capacity,
            "min_capacity": self.min_capacity,
            "verification_interval": self.verification_interval,
            "environmental_conditions": self.environmental_conditions,
            "overall_status": self.overall_status,
            "sha256_hash": self.sha256_hash,
            "pdf_path": self.pdf_path,
            "docx_path": self.docx_path,
            "nameplate_photo_path": self.nameplate_photo_path,
            "display_photo_path": self.display_photo_path,
            "has_manual_override": self.has_manual_override,
            "override_details": self.override_details,
            "supervisor_status": self.supervisor_status or "PENDING_REVIEW",
            "supervisor_remarks": self.supervisor_remarks or "",
            "supervisor_name": self.supervisor_name or "",
            "supervisor_signed_at": self.supervisor_signed_at.strftime("%Y-%m-%d %H:%M:%S") if self.supervisor_signed_at else None,
            "observations": json.loads(self.observations_json) if self.observations_json else [],
            "eccentricity": json.loads(self.eccentricity_json) if self.eccentricity_json else None,
            "repeatability": json.loads(self.repeatability_json) if self.repeatability_json else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }


def init_db():
    """Initializes tables using SQLAlchemy metadata and migrates any missing columns."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        if "test_reports" in insp.get_table_names():
            existing_cols = {c["name"] for c in insp.get_columns("test_reports")}
            needed_cols = [
                ("officer_name", "VARCHAR(128) DEFAULT 'Insp. Rajesh Sharma'"),
                ("officer_badge", "VARCHAR(64) DEFAULT 'RRSL-DOCA-2026-449'"),
                ("environmental_conditions", "VARCHAR(128) DEFAULT '22.5 C | 50% RH'"),
                ("docx_path", "VARCHAR(256) DEFAULT ''"),
                ("nameplate_photo_path", "VARCHAR(256)"),
                ("display_photo_path", "VARCHAR(256)"),
                ("has_manual_override", "INTEGER DEFAULT 0"),
                ("override_details", "TEXT"),
                ("observations_json", "TEXT"),
                ("eccentricity_json", "TEXT"),
                ("repeatability_json", "TEXT"),
                ("supervisor_status", "VARCHAR(32) DEFAULT 'PENDING_REVIEW'"),
                ("supervisor_remarks", "TEXT"),
                ("supervisor_name", "VARCHAR(128)"),
                ("supervisor_signed_at", "DATETIME"),
            ]
            for col_name, col_def in needed_cols:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE test_reports ADD COLUMN {col_name} {col_def}"))
            conn.commit()


def review_report(report_id: str, supervisor_name: str, status: str, remarks: str = "") -> Optional[Dict[str, Any]]:
    """Supervisor selective approval / rejection workflow."""
    db: Session = SessionLocal()
    try:
        stmt = select(TestReport).where(TestReport.report_id == report_id)
        report = db.scalars(stmt).first()
        if not report:
            return None
        report.supervisor_status = status
        report.supervisor_name = supervisor_name
        report.supervisor_remarks = remarks
        report.supervisor_signed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(report)
        return report.to_dict()
    finally:
        db.close()


def get_db():
    """Database session generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_report(report_data: dict, sha256_hash: str, pdf_path: str, docx_path: str,
                nameplate_photo_path: Optional[str] = None,
                display_photo_path: Optional[str] = None,
                has_override: bool = False,
                override_details: str = "") -> TestReport:
    """
    Persists test report, evidence links, and cryptographic signature in SQLite.
    """
    db: Session = SessionLocal()
    try:
        report = TestReport(
            report_id=report_data.get("report_id"),
            officer_name=report_data.get("officer_name", "Insp. Rajesh Sharma"),
            officer_badge=report_data.get("officer_badge", "RRSL-DOCA-2026-449"),
            manufacturer=report_data.get("manufacturer", "Eagle Scales Pvt Ltd"),
            model=report_data.get("model", "DS-215"),
            serial_no=report_data.get("serial_no", "SN-2026-98124"),
            accuracy_class=report_data.get("accuracy_class", "Class III"),
            max_capacity=float(report_data.get("max_cap", 30.0)),
            min_capacity=float(report_data.get("min_cap", 100.0)),
            verification_interval=float(report_data.get("e_val", 5.0)),
            environmental_conditions=report_data.get("environmental_conditions", "22.5°C | 50% RH"),
            overall_status=report_data.get("overall_status", "PASS"),
            sha256_hash=sha256_hash,
            pdf_path=pdf_path,
            docx_path=docx_path,
            nameplate_photo_path=nameplate_photo_path,
            display_photo_path=display_photo_path,
            has_manual_override=1 if has_override else 0,
            override_details=override_details or "",
            observations_json=json.dumps(report_data.get("weighing_observations", [])),
            eccentricity_json=json.dumps(report_data.get("eccentricity_test")) if report_data.get("eccentricity_test") else None,
            repeatability_json=json.dumps(report_data.get("repeatability_test")) if report_data.get("repeatability_test") else None
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    finally:
        db.close()


def get_all_reports(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves all reports ordered by creation time descending."""
    db: Session = SessionLocal()
    try:
        stmt = select(TestReport).order_by(desc(TestReport.id)).limit(limit)
        results = db.scalars(stmt).all()
        return [r.to_dict() for r in results]
    finally:
        db.close()


def get_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves single report record by unique report_id."""
    db: Session = SessionLocal()
    try:
        stmt = select(TestReport).where(TestReport.report_id == report_id)
        report = db.scalars(stmt).first()
        return report.to_dict() if report else None
    finally:
        db.close()


def verify_hash(report_id: str, submitted_hash: str) -> Dict[str, Any]:
    """
    Verifies cryptographic hash against the immutable ledger.
    """
    db: Session = SessionLocal()
    try:
        stmt = select(TestReport).where(TestReport.report_id == report_id)
        report = db.scalars(stmt).first()
        if not report:
            return {
                "found": False,
                "verified": False,
                "message": f"Report ID '{report_id}' was not found in central DoCA registry."
            }

        is_valid = report.sha256_hash.strip().lower() == submitted_hash.strip().lower()
        return {
            "found": True,
            "verified": is_valid,
            "record": report.to_dict(),
            "stored_hash": report.sha256_hash,
            "submitted_hash": submitted_hash,
            "message": (
                "CRYPTOGRAPHIC HASH MATCHED — Official Section 63 BSA 2023 Untampered Document Verified."
                if is_valid
                else "HASH MISMATCH — Potential Data Tampering or Forged Certificate Detected!"
            )
        }
    finally:
        db.close()
