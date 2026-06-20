"""The domain data model — the P0 spine (BUILD_PLAN.md §3).

    Tenant → User → Client → Program → Claim → Designation★
    plus ImportEntryLine, ExportLine, Document, ChecklistItem, Task, AuditEvent

★ The ``Designation`` is the unit of recovery — one matched (import line → export line) assignment
within a claim, carrying its provision, per-unit/total recovery, confidence, headline flag, and the
engine's full glass-box ``trace``. In M1 the **designation ledger** service enforces, across *all*
claims and over time, that ``Σ designated ≤ available`` per import line — making double-designation
(19 U.S.C. 1313(v)) structurally impossible. M0 lays down the schema these controls will guard.

Design notes:
* This module deliberately does **not** use ``from __future__ import annotations`` — SQLAlchemy 2.0
  resolves the ``Mapped[...]`` annotations at class-definition time, and real (non-stringized)
  annotations are the most robust path on Python 3.9. Every column passes an explicit type, so the
  annotation is consulted only for nullability.
* Money is the lossless :class:`server.db.types.Money` (Decimal-exact). Enums are portable
  non-native ``VARCHAR + CHECK``. PKs are string UUIDs (non-sequential, multi-tenant friendly).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.db.base import Base
from server.db.types import Money
from server.domain.enums import (
    ChecklistStatus,
    ClaimMode,
    ClaimStatus,
    DocStatus,
    DocType,
    DrawbackType,
    TaskKind,
    TaskStatus,
    TenantKind,
    UserRole,
)


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enum(py_enum, name: str) -> SAEnum:
    """Portable VARCHAR+CHECK enum (named, so Alembic/SQLite-batch migrations stay stable)."""
    return SAEnum(py_enum, name=name, native_enum=False, length=32, validate_strings=True)


class Entity:
    """Mixin: string-UUID primary key + creation timestamp, shared by every domain table."""

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# Tenancy & identity
# ─────────────────────────────────────────────────────────────────────────────
class Tenant(Entity, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[TenantKind] = mapped_column(_enum(TenantKind, "tenant_kind"), nullable=False)

    clients: Mapped[List["Client"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan")


class User(Entity, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"), nullable=False)
    # A "client" role user is scoped to exactly one Client (read-only). Null for staff roles.
    client_scope_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("clients.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Client(Entity, Base):
    """The importer of record whose drawback the tenant prepares."""

    __tablename__ = "clients"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    importer_id: Mapped[str] = mapped_column(String(32), nullable=False)  # IRS/EIN
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="clients")
    programs: Mapped[List["Program"]] = relationship(
        back_populates="client", cascade="all, delete-orphan")


class Program(Entity, Base):
    """A drawback program for a client: a provision type + its configuration (privileges, accounting
    method, eligible layers, manufacturing ruling). Drives the checklist and engine parameters."""

    __tablename__ = "programs"

    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    drawback_type: Mapped[DrawbackType] = mapped_column(
        _enum(DrawbackType, "drawback_type"), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    mfg_ruling_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="programs")
    claims: Mapped[List["Claim"]] = relationship(
        back_populates="program", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Claims & the designation ledger
# ─────────────────────────────────────────────────────────────────────────────
class Claim(Entity, Base):
    __tablename__ = "claims"

    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"), nullable=False, index=True)
    period: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mode: Mapped[ClaimMode] = mapped_column(
        _enum(ClaimMode, "claim_mode"), default=ClaimMode.retroactive, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(
        _enum(ClaimStatus, "claim_status"), default=ClaimStatus.draft, nullable=False, index=True)

    filed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    liquidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # The three money figures the ledger tracks over the lifecycle (BUILD_PLAN §3).
    estimated_refund: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    defensible_refund: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    actual_refund: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)

    claim_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    signoff: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Provenance: which dated engine config produced these numbers (re-verify before real use).
    tariff_config_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    as_of: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    program: Mapped["Program"] = relationship(back_populates="claims")
    designations: Mapped[List["Designation"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan")


class ImportEntryLine(Entity, Base):
    """A CBP 7501 / ACE entry-summary line — the duty-paid import a claim designates against."""

    __tablename__ = "import_entry_lines"
    __table_args__ = (UniqueConstraint("client_id", "entry_number", "line_no"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    entry_number: Mapped[str] = mapped_column(String(32), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    hts10: Mapped[str] = mapped_column(String(10), nullable=False)
    import_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    entered_value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    # {charge_type_value: decimal_string} — the duty/tax/fee components on the line.
    charges: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    liquidated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_document_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("documents.id"), nullable=True)


class ExportLine(Entity, Base):
    """An export or destruction event — AES/EEI or bill-of-lading derived. Identified within a client
    by its ``reference`` (BOL / AES ITN / invoice) so the same export can't be claimed twice."""

    __tablename__ = "export_lines"
    __table_args__ = (UniqueConstraint("client_id", "reference"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    hts10: Mapped[str] = mapped_column(String(10), nullable=False)
    export_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    value_per_unit: Mapped[Decimal] = mapped_column(Money, nullable=False)
    has_export_proof: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    itn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    proof_document_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("documents.id"), nullable=True)
    # Optional explicit direct-identification link to a specific import lot (enables a (j)(1) arc).
    direct_id_entry: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    direct_id_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Designation(Entity, Base):
    """★ One import-line → export-line assignment within a claim — the unit of recovery and the
    row the across-time conservation invariant (M1) guards (Σ designated ≤ available)."""

    __tablename__ = "designations"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False, index=True)
    import_entry_line_id: Mapped[str] = mapped_column(
        ForeignKey("import_entry_lines.id"), nullable=False, index=True)
    export_line_id: Mapped[str] = mapped_column(
        ForeignKey("export_lines.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    provision: Mapped[str] = mapped_column(String(8), nullable=False)  # CATAIR provision code
    # The eligible per-unit import duty this designation draws from the import line — constant per
    # import line, so it lets the ledger express the conservation in duty as well as quantity.
    per_unit_designated_duty: Mapped[Decimal] = mapped_column(Money, nullable=False)
    per_unit_recovery: Mapped[Decimal] = mapped_column(Money, nullable=False)
    recovery: Mapped[Decimal] = mapped_column(Money, nullable=False)
    recovery_low: Mapped[Decimal] = mapped_column(Money, nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    in_headline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trace: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # the glass-box basis

    claim: Mapped["Claim"] = relationship(back_populates="designations")
    import_line: Mapped["ImportEntryLine"] = relationship()
    export_line: Mapped["ExportLine"] = relationship()


# ─────────────────────────────────────────────────────────────────────────────
# Documents, checklist, tasks, audit
# ─────────────────────────────────────────────────────────────────────────────
class Document(Entity, Base):
    """An uploaded source document. OCR *proposes* extracted fields (status ``needs_review``); a
    human *confirms* before anything is trusted — nothing here auto-files (M4)."""

    __tablename__ = "documents"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    doc_type: Mapped[DocType] = mapped_column(
        _enum(DocType, "doc_type"), default=DocType.other, nullable=False)
    blob_ref: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[DocStatus] = mapped_column(
        _enum(DocStatus, "doc_status"), default=DocStatus.uploaded, nullable=False, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    claim_id: Mapped[Optional[str]] = mapped_column(ForeignKey("claims.id"), nullable=True)
    retention_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ChecklistItem(Entity, Base):
    """A required/optional document or data item for a claim. The set reconfigures by drawback type
    + program config (M5); satisfying all required items is the 'complete claim' gate (190.51)."""

    __tablename__ = "checklist_items"

    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    satisfied_by_document_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("documents.id"), nullable=True)
    status: Mapped[ChecklistStatus] = mapped_column(
        _enum(ChecklistStatus, "checklist_status"), default=ChecklistStatus.pending, nullable=False)


class Task(Entity, Base):
    """A Gaps & Chase work item: a missing document/data point with an owner and (optionally) a
    one-click client request (M5)."""

    __tablename__ = "tasks"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    claim_id: Mapped[Optional[str]] = mapped_column(ForeignKey("claims.id"), nullable=True, index=True)
    kind: Mapped[TaskKind] = mapped_column(_enum(TaskKind, "task_kind"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        _enum(TaskStatus, "task_status"), default=TaskStatus.open, nullable=False, index=True)
    # Free-form reference to a related import/export line (kept type-agnostic for M0).
    related_line_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    client_request_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)


class AuditEvent(Entity, Base):
    """An append-only record of every consequential state change (who/what/when/detail)."""

    __tablename__ = "audit_events"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(32), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
