"""Database configuration and ORM models for the MSME platform."""

from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Generator

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger(__name__)


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./msme.db")
Base = declarative_base()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache the SQLAlchemy engine."""
    database_url = os.getenv("DATABASE_URL", DATABASE_URL)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, echo=False)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BusinessProfile(Base):
    """Store the primary business identity details."""

    __tablename__ = "business_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_name = Column(String(255), nullable=False)
    gst_number = Column(String(32), nullable=True)
    owner_name = Column(String(255), nullable=True)
    preferred_language = Column(String(16), nullable=False, default="en")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Invoice(Base):
    """Store invoice records and payment metadata."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(64), unique=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(32), nullable=True)
    customer_gstin = Column(String(32), nullable=True)
    line_items = Column(Text, nullable=False)
    subtotal = Column(Float, nullable=False)
    cgst = Column(Float, nullable=False, default=0.0)
    sgst = Column(Float, nullable=False, default=0.0)
    igst = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    irn = Column(String(128), nullable=True)
    upi_qr_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)


class InventoryItem(Base):
    """Track stock, pricing, and reorder thresholds."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False, default="pcs")
    reorder_level = Column(Float, nullable=False, default=10.0)
    cost_price = Column(Float, nullable=True)
    selling_price = Column(Float, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    location = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    """Store ledger-aligned income and expense transactions."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    txn_date = Column(DateTime, nullable=False)
    description = Column(String(512), nullable=False)
    amount = Column(Float, nullable=False)
    txn_type = Column(String(32), nullable=False)
    category = Column(String(128), nullable=True)
    bank_ref = Column(String(128), nullable=True)
    tally_ref = Column(String(128), nullable=True)
    reconciled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Employee(Base):
    """Store employee master data and salary components."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_code = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(32), nullable=True)
    pan = Column(String(32), nullable=True)
    designation = Column(String(128), nullable=True)
    basic_salary = Column(Float, nullable=False)
    hra = Column(Float, nullable=False, default=0.0)
    da = Column(Float, nullable=False, default=0.0)
    allowances = Column(Float, nullable=False, default=0.0)
    pf_applicable = Column(Boolean, nullable=False, default=True)
    esi_applicable = Column(Boolean, nullable=False, default=False)
    joined_at = Column(DateTime, nullable=True)
    active = Column(Boolean, nullable=False, default=True)


class PayrollRun(Base):
    """Store payroll execution results for each employee and month."""

    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_month = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    gross = Column(Float, nullable=False)
    pf_deduction = Column(Float, nullable=False, default=0.0)
    esi_deduction = Column(Float, nullable=False, default=0.0)
    tds_deduction = Column(Float, nullable=False, default=0.0)
    net_pay = Column(Float, nullable=False)
    payslip_path = Column(String(512), nullable=True)
    neft_included = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Customer(Base):
    """Store customer profiles and purchase segmentation."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(32), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    gstin = Column(String(32), nullable=True)
    total_spent = Column(Float, nullable=False, default=0.0)
    purchase_count = Column(Integer, nullable=False, default=0)
    last_purchase_date = Column(DateTime, nullable=True)
    total_purchases = Column(Float, nullable=False, default=0.0)
    last_purchase_at = Column(DateTime, nullable=True)
    segment = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class CustomerPurchaseHistory(Base):
    """Store customer purchase events for CRM history and segmentation."""

    __tablename__ = "customer_purchase_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    source_event_id = Column(String(64), unique=True, nullable=True)
    invoice_reference = Column(String(64), nullable=True)
    line_items = Column(Text, nullable=False)
    total = Column(Float, nullable=False)
    purchase_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    source = Column(String(64), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class CampaignLog(Base):
    """Store outbound campaign execution metrics."""

    __tablename__ = "campaign_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String(255), nullable=False)
    segment = Column(String(128), nullable=False)
    message_template = Column(Text, nullable=False)
    sent_count = Column(Integer, nullable=False, default=0)
    delivered_count = Column(Integer, nullable=False, default=0)
    read_count = Column(Integer, nullable=False, default=0)
    reply_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AgentLog(Base):
    """Store orchestration traces and outcomes for agent tasks."""

    __tablename__ = "agent_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(128), nullable=False)
    task_id = Column(String(64), unique=True, nullable=False)
    trigger_type = Column(String(64), nullable=False)
    trigger_payload = Column(Text, nullable=False)
    steps = Column(Text, nullable=False)
    outcome = Column(String(32), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)


class HITLRequest(Base):
    """Store human approval requests raised by autonomous agents."""

    __tablename__ = "hitl_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("agent_log.task_id"), nullable=False)
    agent_name = Column(String(128), nullable=False)
    action_type = Column(String(64), nullable=False)
    action_preview = Column(Text, nullable=False)
    risk_flag = Column(String(16), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    owner_decision = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=24))


def init_db() -> None:
    """Create all configured database tables."""
    Base.metadata.create_all(bind=get_engine())


def get_encryption_key() -> bytes:
    """Read and validate the encryption key from the environment."""
    raw_key = os.getenv("ENCRYPTION_KEY")
    if not raw_key:
        raise ValueError("ENCRYPTION_KEY is missing from the environment.")

    try:
        key_bytes = bytes.fromhex(raw_key)
    except ValueError as exc:
        raise ValueError("ENCRYPTION_KEY must be a valid hex string.") from exc

    if len(key_bytes) != 32:
        raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes.")

    return key_bytes


if __name__ == "__main__":
    init_db()
    print("Database initialised successfully.")
