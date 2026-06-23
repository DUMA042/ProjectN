"""
owl.load.models
~~~~~~~~~~~~~~~
SQLAlchemy 2.x ORM models — EXACTLY aligned with the existing database.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy import (
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Interval,
    String,
    Text,
    func,
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
    status_name: Mapped[str] = mapped_column(String(100), unique=True)

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

class Department(Base):
    __tablename__ = "departments"
    department_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_name: Mapped[str] = mapped_column(String(255), unique=True)

class GradeLevel(Base):
    __tablename__ = "grade_levels"
    gl_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gl_name: Mapped[str] = mapped_column(String(50), unique=True)

class LeaveType(Base):
    __tablename__ = "leave_types"
    leave_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    leave_type_name: Mapped[str] = mapped_column(String(100), unique=True)


# ── Core Entities ─────────────────────────────────────────────────────────────

class Employee(Base):
    """Actual Physical Table: 'employees'."""
    __tablename__ = "employees"

    id_no: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sex: Mapped[Optional[str]] = mapped_column(String(20))

    rank_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ranks.rank_id"))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.department_id"))
    gl_id: Mapped[Optional[int]] = mapped_column(ForeignKey("grade_levels.gl_id"))
    emp_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employment_types.emp_type_id"))
    status_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employee_statuses.status_id"))
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))

    geographical_zone: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_last_deployment: Mapped[Optional[date]] = mapped_column(Date)
    phone_number: Mapped[Optional[str]] = mapped_column(String(30))
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

class EmployeeLocationHistory(Base):
    __tablename__ = "employee_location_history"
    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no"))
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

class EmployeeDepartmentHistory(Base):
    __tablename__ = "employee_department_history"
    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no"))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.department_id"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

class EmployeeGLHistory(Base):
    __tablename__ = "employee_gl_history"
    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no"))
    gl_id: Mapped[Optional[int]] = mapped_column(ForeignKey("grade_levels.gl_id"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

class EmployeeRankHistory(Base):
    __tablename__ = "employee_rank_history"
    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no"))
    rank_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ranks.rank_id"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

class LeaveApplication(Base):
    __tablename__ = "leave_applications"
    application_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no"))
    proposed_leave_date: Mapped[Optional[date]] = mapped_column(Date)
    proposed_leave_date_raw: Mapped[Optional[str]] = mapped_column(String(255))
    resumption_date: Mapped[Optional[date]] = mapped_column(Date)
    forfeiture: Mapped[Optional[str]] = mapped_column(String(255))
    issuance_date: Mapped[Optional[date]] = mapped_column(Date)
    issuance_date_raw: Mapped[Optional[str]] = mapped_column(String(255))
    remark: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class LeaveRecord(Base):
    __tablename__ = "leave_records"
    record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leave_applications.application_id", ondelete="CASCADE"))
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no"))
    leave_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leave_types.leave_type_id"))
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    start_date_raw: Mapped[Optional[str]] = mapped_column(String(255))
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date_raw: Mapped[Optional[str]] = mapped_column(String(255))
    planned_start_date: Mapped[Optional[date]] = mapped_column(Date)
    planned_start_date_raw: Mapped[Optional[str]] = mapped_column(String(255))
    planned_end_date: Mapped[Optional[date]] = mapped_column(Date)
    planned_end_date_raw: Mapped[Optional[str]] = mapped_column(String(255))


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
    period: Mapped[Optional[date]] = mapped_column(Date, Computed("make_date((substring(split_part(normalized_filename, '_'::text, 3) from 1 for 4))::integer, (substring(split_part(normalized_filename, '_'::text, 3) from 5 for 2))::integer, 1)", persisted=True))
    version: Mapped[Optional[int]] = mapped_column(Integer)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), server_default="pending", nullable=False)
    error_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Kanban Board Entities ─────────────────────────────────────────────────────

class KanbanBoard(Base):
    __tablename__ = "kanban_boards"
    board_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.department_id", ondelete="SET NULL"))
    is_archived: Mapped[bool] = mapped_column(server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class KanbanColumn(Base):
    __tablename__ = "kanban_columns"
    column_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.board_id", ondelete="CASCADE"), nullable=False)
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7))
    is_done_column: Mapped[bool] = mapped_column(server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class KanbanLabel(Base):
    __tablename__ = "kanban_labels"
    label_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7))

class KanbanTask(Base):
    __tablename__ = "kanban_tasks"
    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.board_id", ondelete="CASCADE"), nullable=False)
    column_id: Mapped[int] = mapped_column(ForeignKey("kanban_columns.column_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), server_default="medium", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    position: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_archived: Mapped[bool] = mapped_column(server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class KanbanTaskAssignee(Base):
    __tablename__ = "kanban_task_assignees"
    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("kanban_tasks.task_id", ondelete="CASCADE"), nullable=False)
    id_no: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("employees.id_no", ondelete="SET NULL"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_by: Mapped[Optional[str]] = mapped_column(String(64))

class KanbanTaskLabel(Base):
    __tablename__ = "kanban_task_labels"
    task_id: Mapped[int] = mapped_column(ForeignKey("kanban_tasks.task_id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[int] = mapped_column(ForeignKey("kanban_labels.label_id", ondelete="CASCADE"), primary_key=True)

class KanbanTaskHistory(Base):
    __tablename__ = "kanban_task_history"
    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("kanban_tasks.task_id", ondelete="CASCADE"), nullable=False)
    from_column_id: Mapped[Optional[int]] = mapped_column(ForeignKey("kanban_columns.column_id"))
    to_column_id: Mapped[int] = mapped_column(ForeignKey("kanban_columns.column_id"), nullable=False)
    moved_by: Mapped[Optional[str]] = mapped_column(String(64))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_in_previous: Mapped[Optional[timedelta]] = mapped_column(Interval)
