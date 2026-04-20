"""
owl.load.models
~~~~~~~~~~~~~~~
SQLAlchemy 2.x ORM models — EXACTLY aligned with the existing database.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    FetchedValue,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ── Base ──────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Supporting Dimensions ───────────────────────────────────────────────────

class Unit(Base):
    __tablename__ = "units"
    unit_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_name: Mapped[str] = mapped_column(String(255), unique=True)

class Rank(Base):
    __tablename__ = "ranks"
    rank_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rank_name: Mapped[str] = mapped_column(String(255), unique=True)

class EmploymentType(Base):
    __tablename__ = "employment_types"
    emp_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emp_type_name: Mapped[str] = mapped_column(String(50), unique=True)

class EmployeeStatus(Base):
    __tablename__ = "employee_statuses"
    status_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status_name: Mapped[str] = mapped_column(String(50), unique=True)

class Venue(Base):
    __tablename__ = "venues"
    venue_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue_name: Mapped[str] = mapped_column(String(255), unique=True)

class Consultant(Base):
    __tablename__ = "consultants"
    consultant_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consultant_name: Mapped[str] = mapped_column(String(255), unique=True)

class Location(Base):
    __tablename__ = "locations"
    location_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_name: Mapped[str] = mapped_column(String(128), unique=True)


# ── Core Entities ─────────────────────────────────────────────────────────────

class Employee(Base):
    """Actual Physical Table: 'employees'."""
    __tablename__ = "employees"

    id_no: Mapped[str] = mapped_column(String(64), primary_key=True)
    serial_no: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, info={"label": "S/N"})
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sex: Mapped[Optional[str]] = mapped_column(String(20))
    
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.unit_id"))
    rank_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ranks.rank_id"))
    emp_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employment_types.emp_type_id"))
    status_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employee_statuses.status_id"))
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))
    
    remark: Mapped[Optional[str]] = mapped_column(Text)

class EmployeeCardSwipe(Base):
    __tablename__ = "employee_card_swipes"
    swipe_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[str] = mapped_column(ForeignKey("employees.id_no"), nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))
    swipe_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class EmployeeTraining(Base):
    __tablename__ = "employee_trainings"
    training_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[str] = mapped_column(ForeignKey("employees.id_no"), nullable=False)
    venue_id: Mapped[Optional[int]] = mapped_column(ForeignKey("venues.venue_id"))
    consultant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("consultants.consultant_id"))
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

class EmployeeHistory(Base):
    __tablename__ = "employee_history"
    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[str] = mapped_column(ForeignKey("employees.id_no"), nullable=False, index=True)
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.unit_id"))
    rank_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ranks.rank_id"))
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Quarantine Entities (Orphans) ─────────────────────────────────────────────

class QuarantineCardSwipe(Base):
    """Stores card swipe records for ID_NOs that do not exist in 'employees'."""
    __tablename__ = "quarantine_card_swipes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    employee_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(128))
    swipe_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class QuarantineTraining(Base):
    """Stores training records for ID_NOs that do not exist in 'employees'."""
    __tablename__ = "quarantine_trainings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[str] = mapped_column(String(64), nullable=False)
    venue_name: Mapped[Optional[str]] = mapped_column(String(255))
    consultant_name: Mapped[Optional[str]] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Ingestion Metadata ───────────────────────────────────────────────────────

class FileIngestionMeta(Base):
    __tablename__ = "file_ingestion_meta"
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_filename: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(128))
    report_type: Mapped[Optional[str]] = mapped_column(String(128))
    period: Mapped[Optional[date]] = mapped_column(Date, server_default=FetchedValue())
    version: Mapped[Optional[int]] = mapped_column(Integer)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), server_default="pending", nullable=False)
    error_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
