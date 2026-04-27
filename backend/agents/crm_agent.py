"""CRM agent implementation for customer intelligence and retention workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, inspect, text

from agents.hitl import HITLActionType, RiskFlag, hitl_gate
from agents.memory import memory_store
from agents.orchestrator import AGENT_REGISTRY
from agents.tools import TOOL_MAP, create_hitl_request, send_whatsapp
from core.db import CampaignLog, Customer, CustomerPurchaseHistory, SessionLocal, get_engine, init_db
from core.ws_manager import MessageType, build_ws_message, ws_manager

logger = logging.getLogger(__name__)
_ = (create_hitl_request, send_whatsapp)

ACTIVE_WINDOW_DAYS = 7
WARM_WINDOW_DAYS = 30
DEFAULT_INACTIVE_DAYS = 30
DEFAULT_DISCOUNT_PERCENTAGE = 10


class CRMAgent:
    """Manage customer profiles, segments, and campaign suggestions."""

    def __init__(self) -> None:
        """Initialise the CRM agent and ensure CRM schema compatibility."""
        init_db()
        self.name = "crm_agent"
        self._ensure_schema()
        logger.info("[CRMAgent] Initialised")

    def _ensure_schema(self) -> None:
        """Create missing CRM tables and columns for existing SQLite databases."""
        engine = get_engine()
        inspector = inspect(engine)
        customer_columns = {column["name"] for column in inspector.get_columns("customers")}
        missing_columns = {
            "total_spent": "ALTER TABLE customers ADD COLUMN total_spent FLOAT NOT NULL DEFAULT 0.0",
            "purchase_count": "ALTER TABLE customers ADD COLUMN purchase_count INTEGER NOT NULL DEFAULT 0",
            "last_purchase_date": "ALTER TABLE customers ADD COLUMN last_purchase_date DATETIME",
        }

        with engine.begin() as connection:
            for column_name, ddl in missing_columns.items():
                if column_name not in customer_columns:
                    connection.execute(text(ddl))

            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS customer_purchase_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        source_event_id VARCHAR(64) UNIQUE,
                        invoice_reference VARCHAR(64),
                        line_items TEXT NOT NULL,
                        total FLOAT NOT NULL,
                        purchase_date DATETIME NOT NULL,
                        source VARCHAR(64),
                        metadata_json TEXT,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(customer_id) REFERENCES customers(id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_customer_purchase_history_customer "
                    "ON customer_purchase_history(customer_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_customer_purchase_history_date "
                    "ON customer_purchase_history(purchase_date)"
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE customers
                    SET total_spent = COALESCE(total_purchases, 0.0)
                    WHERE total_purchases IS NOT NULL
                      AND COALESCE(total_spent, 0.0) = 0.0
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE customers
                    SET last_purchase_date = last_purchase_at
                    WHERE last_purchase_date IS NULL
                      AND last_purchase_at IS NOT NULL
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE customers
                    SET purchase_count = CASE
                        WHEN COALESCE(total_spent, total_purchases, 0.0) > 0 THEN 1
                        ELSE 0
                    END
                    WHERE COALESCE(purchase_count, 0) = 0
                      AND (last_purchase_date IS NOT NULL OR last_purchase_at IS NOT NULL)
                    """
                )
            )

    def _success(self, message: str, data: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
        """Build a standard success payload for orchestrator and direct callers."""
        payload = {
            "status": "success",
            "message": message,
            "data": data or {},
            "success": True,
            "summary": message,
            "error": None,
        }
        payload.update(extra)
        return payload

    def _error(
        self,
        message: str,
        error: str,
        data: dict[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build a standard error payload for orchestrator and direct callers."""
        payload = {
            "status": "error",
            "message": message,
            "data": data or {},
            "success": False,
            "summary": message,
            "error": error,
        }
        payload.update(extra)
        return payload

    def _log_step(self, task_id: str | None, role: str, content: str) -> None:
        """Append a scratchpad step when a task context exists."""
        if task_id:
            memory_store.stm_append_step(task_id, role, content)

    async def _broadcast_update(self, task_id: str, status: str, data: dict[str, Any]) -> None:
        """Broadcast CRM-specific progress updates to the dashboard."""
        await ws_manager.broadcast(
            build_ws_message(
                MessageType.AGENT_UPDATE,
                agent=self.name,
                data={
                    "task_id": task_id,
                    "status": status,
                    **data,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
            room="dashboard",
        )

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        """Convert a raw value into a float with a safe default."""
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse common timestamp formats from event payloads."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        raw_value = str(value).strip()
        if not raw_value:
            return None

        normalized = raw_value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass

        for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw_value, date_format)
            except ValueError:
                continue
        return None

    def _segment_for_date(self, last_purchase_date: datetime | None) -> str:
        """Classify a customer into a simple recency-based segment."""
        if not last_purchase_date:
            return "Inactive"

        days_since_last_purchase = max((datetime.utcnow() - last_purchase_date).days, 0)
        if days_since_last_purchase < ACTIVE_WINDOW_DAYS:
            return "Active"
        if days_since_last_purchase <= WARM_WINDOW_DAYS:
            return "Warm"
        return "Inactive"

    def _build_customer_phone(self, customer_data: dict[str, Any]) -> str:
        """Resolve a stable customer key for the phone column when data is incomplete."""
        phone = str(customer_data.get("phone") or "").strip()
        if phone:
            return phone

        name = str(customer_data.get("name") or "customer").strip().lower()
        email = str(customer_data.get("email") or "").strip().lower()
        gstin = str(customer_data.get("gstin") or "").strip().upper()
        stable_seed = "|".join(part for part in [name, email, gstin] if part) or uuid.uuid4().hex
        return f"unknown::{uuid.uuid5(uuid.NAMESPACE_DNS, stable_seed).hex[:12]}"

    def _is_contactable_phone(self, phone: str | None) -> bool:
        """Return whether the stored phone number can be used for WhatsApp."""
        return bool(phone and not str(phone).startswith("unknown::"))

    def _serialize_customer(self, customer: Customer) -> dict[str, Any]:
        """Convert a customer record into a JSON-friendly dict."""
        total_spent = float(customer.total_spent or customer.total_purchases or 0.0)
        last_purchase_date = customer.last_purchase_date or customer.last_purchase_at
        return {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "gstin": customer.gstin,
            "total_spent": total_spent,
            "purchase_count": int(customer.purchase_count or 0),
            "last_purchase_date": last_purchase_date.isoformat() if last_purchase_date else None,
            "segment": customer.segment or self._segment_for_date(last_purchase_date),
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "contactable": self._is_contactable_phone(customer.phone),
        }

    def _serialize_history(self, history_row: CustomerPurchaseHistory) -> dict[str, Any]:
        """Convert a purchase history record into a JSON-friendly dict."""
        try:
            items = json.loads(history_row.line_items)
        except (TypeError, ValueError):
            items = []
        try:
            metadata = json.loads(history_row.metadata_json) if history_row.metadata_json else {}
        except (TypeError, ValueError):
            metadata = {}
        return {
            "id": history_row.id,
            "customer_id": history_row.customer_id,
            "source_event_id": history_row.source_event_id,
            "invoice_reference": history_row.invoice_reference,
            "items": items,
            "total": float(history_row.total or 0.0),
            "purchase_date": history_row.purchase_date.isoformat() if history_row.purchase_date else None,
            "source": history_row.source,
            "metadata": metadata,
            "created_at": history_row.created_at.isoformat() if history_row.created_at else None,
        }

    def _find_customer(
        self,
        db: Any,
        *,
        customer_id: int | None = None,
        phone: str | None = None,
        email: str | None = None,
        gstin: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        """Locate an existing customer using the strongest available identifiers."""
        if customer_id is not None:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if customer:
                return customer

        if phone:
            customer = db.query(Customer).filter(Customer.phone == phone).first()
            if customer:
                return customer

        if gstin:
            customer = db.query(Customer).filter(Customer.gstin == gstin).first()
            if customer:
                return customer

        if email:
            customer = db.query(Customer).filter(func.lower(Customer.email) == email.lower()).first()
            if customer:
                return customer

        if name:
            return db.query(Customer).filter(func.lower(Customer.name) == name.lower()).first()

        return None

    def _get_customer_by_identifier(self, db: Any, payload: dict[str, Any]) -> Customer | None:
        """Resolve a customer from a generic query payload."""
        customer_id = payload.get("customer_id")
        try:
            customer_id = int(customer_id) if customer_id not in (None, "") else None
        except (TypeError, ValueError):
            customer_id = None

        return self._find_customer(
            db,
            customer_id=customer_id,
            phone=str(payload.get("phone") or "").strip() or None,
            email=str(payload.get("email") or "").strip() or None,
            gstin=str(payload.get("gstin") or "").strip() or None,
            name=str(payload.get("name") or "").strip() or None,
        )

    def _resolve_purchase_date(self, payload: dict[str, Any], event_timestamp: str | None) -> datetime:
        """Pick the best available purchase timestamp from an event payload."""
        for candidate in (
            payload.get("purchase_date"),
            payload.get("invoice_date"),
            payload.get("created_at"),
            event_timestamp,
        ):
            parsed = self._parse_datetime(candidate)
            if parsed:
                return parsed
        return datetime.utcnow()

    def _extract_customer_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalise billing payload shapes into a CRM customer dict."""
        customer_data = dict(payload.get("customer") or payload.get("buyer") or {})
        if not customer_data:
            customer_data = {
                "name": payload.get("customer_name"),
                "phone": payload.get("customer_phone"),
                "gstin": payload.get("customer_gstin"),
                "email": payload.get("customer_email"),
            }
        return customer_data

    def _upsert_customer_purchase(
        self,
        *,
        event_id: str | None,
        source: str,
        invoice_reference: str | None,
        customer_data: dict[str, Any],
        items: list[dict[str, Any]],
        total: float,
        purchase_date: datetime,
        event_payload: dict[str, Any],
    ) -> tuple[Customer, CustomerPurchaseHistory | None, bool]:
        """Upsert a customer profile and append a purchase history entry."""
        db = SessionLocal()
        try:
            resolved_phone = self._build_customer_phone(customer_data)
            customer = self._find_customer(
                db,
                phone=resolved_phone,
                email=str(customer_data.get("email") or "").strip() or None,
                gstin=str(customer_data.get("gstin") or "").strip() or None,
                name=str(customer_data.get("name") or "").strip() or None,
            )

            created = False
            if not customer:
                customer = Customer(
                    name=str(customer_data.get("name") or "Unknown Customer").strip(),
                    phone=resolved_phone,
                    email=str(customer_data.get("email") or "").strip() or None,
                    gstin=str(customer_data.get("gstin") or "").strip() or None,
                    total_spent=0.0,
                    purchase_count=0,
                    last_purchase_date=None,
                    total_purchases=0.0,
                    last_purchase_at=None,
                    segment="Inactive",
                    created_at=datetime.utcnow(),
                )
                db.add(customer)
                db.flush()
                created = True
            else:
                if customer_data.get("name"):
                    customer.name = str(customer_data["name"]).strip()
                if customer_data.get("email"):
                    customer.email = str(customer_data["email"]).strip()
                if customer_data.get("gstin"):
                    customer.gstin = str(customer_data["gstin"]).strip()
                if self._is_contactable_phone(resolved_phone) and not self._is_contactable_phone(customer.phone):
                    customer.phone = resolved_phone

            duplicate_history = None
            if event_id:
                duplicate_history = (
                    db.query(CustomerPurchaseHistory)
                    .filter(CustomerPurchaseHistory.source_event_id == event_id)
                    .first()
                )
            if not duplicate_history and invoice_reference:
                duplicate_history = (
                    db.query(CustomerPurchaseHistory)
                    .filter(
                        CustomerPurchaseHistory.customer_id == customer.id,
                        CustomerPurchaseHistory.invoice_reference == invoice_reference,
                    )
                    .first()
                )

            history_row = duplicate_history
            if not duplicate_history:
                customer.total_spent = round(self._coerce_float(customer.total_spent) + total, 2)
                customer.total_purchases = customer.total_spent
                customer.purchase_count = int(customer.purchase_count or 0) + 1
                latest_purchase = customer.last_purchase_date or customer.last_purchase_at
                if not latest_purchase or purchase_date >= latest_purchase:
                    customer.last_purchase_date = purchase_date
                    customer.last_purchase_at = purchase_date
                customer.segment = self._segment_for_date(customer.last_purchase_date)

                history_row = CustomerPurchaseHistory(
                    customer_id=customer.id,
                    source_event_id=event_id,
                    invoice_reference=invoice_reference,
                    line_items=json.dumps(items or [], default=str),
                    total=total,
                    purchase_date=purchase_date,
                    source=source,
                    metadata_json=json.dumps(event_payload, default=str),
                    created_at=datetime.utcnow(),
                )
                db.add(history_row)
            elif not customer.segment:
                customer.segment = self._segment_for_date(customer.last_purchase_date or customer.last_purchase_at)

            db.commit()
            db.refresh(customer)
            if history_row:
                db.refresh(history_row)
            return customer, history_row, created
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_customer(
        self,
        *,
        name: str,
        phone: str,
        email: str | None = None,
        gstin: str | None = None,
    ) -> dict[str, Any]:
        """Create a customer profile if it does not already exist."""
        clean_name = str(name or "").strip()
        clean_phone = str(phone or "").strip()
        if not clean_name:
            return self._error("Customer creation failed", "Customer name is required")
        if not clean_phone:
            return self._error("Customer creation failed", "Customer phone is required")

        db = SessionLocal()
        try:
            existing = self._find_customer(
                db,
                phone=clean_phone,
                email=str(email or "").strip() or None,
                gstin=str(gstin or "").strip() or None,
                name=clean_name,
            )
            if existing:
                return self._success("Customer already exists", {"customer": self._serialize_customer(existing)})

            customer = Customer(
                name=clean_name,
                phone=clean_phone,
                email=str(email or "").strip() or None,
                gstin=str(gstin or "").strip() or None,
                total_spent=0.0,
                purchase_count=0,
                last_purchase_date=None,
                total_purchases=0.0,
                last_purchase_at=None,
                segment="Inactive",
                created_at=datetime.utcnow(),
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            return self._success("Customer created", {"customer": self._serialize_customer(customer)})
        except Exception as exc:
            db.rollback()
            return self._error("Customer creation failed", str(exc))
        finally:
            db.close()

    def update_customer(
        self,
        customer_id: int,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update a customer profile and CRM statistics."""
        db = SessionLocal()
        try:
            customer = self._find_customer(db, customer_id=customer_id)
            if not customer:
                return self._error("Customer not found", f"Customer '{customer_id}' does not exist")

            for field_name in ("name", "phone", "email", "gstin"):
                if updates.get(field_name) not in (None, ""):
                    setattr(customer, field_name, str(updates[field_name]).strip())

            if "total_spent" in updates and updates["total_spent"] is not None:
                customer.total_spent = self._coerce_float(updates["total_spent"])
                customer.total_purchases = customer.total_spent

            if "purchase_count" in updates and updates["purchase_count"] is not None:
                customer.purchase_count = int(updates["purchase_count"])

            last_purchase_date = self._parse_datetime(updates.get("last_purchase_date"))
            if last_purchase_date:
                customer.last_purchase_date = last_purchase_date
                customer.last_purchase_at = last_purchase_date

            customer.segment = str(
                updates.get("segment")
                or self._segment_for_date(customer.last_purchase_date or customer.last_purchase_at)
            )

            db.commit()
            db.refresh(customer)
            return self._success("Customer updated", {"customer": self._serialize_customer(customer)})
        except Exception as exc:
            db.rollback()
            return self._error("Customer update failed", str(exc), {"customer_id": customer_id})
        finally:
            db.close()

    def get_customer(self, customer_id: int) -> dict[str, Any]:
        """Fetch one customer profile by its numeric identifier."""
        db = SessionLocal()
        try:
            customer = self._find_customer(db, customer_id=customer_id)
            if not customer:
                return self._error("Customer not found", f"Customer '{customer_id}' does not exist")
            return self._success("Customer fetched", {"customer": self._serialize_customer(customer)})
        finally:
            db.close()

    def list_customers(self) -> dict[str, Any]:
        """Return all customers ordered by value and recency."""
        db = SessionLocal()
        try:
            customers = (
                db.query(Customer)
                .order_by(Customer.total_spent.desc(), Customer.last_purchase_date.desc())
                .all()
            )
            return self._success(
                "Customer list fetched",
                {
                    "customers": [self._serialize_customer(customer) for customer in customers],
                    "count": len(customers),
                },
            )
        finally:
            db.close()

    def top_customers(self, limit: int = 5) -> dict[str, Any]:
        """Return the highest-value customers by total spend."""
        db = SessionLocal()
        try:
            safe_limit = max(int(limit or 5), 1)
            customers = (
                db.query(Customer)
                .order_by(Customer.total_spent.desc(), Customer.purchase_count.desc())
                .limit(safe_limit)
                .all()
            )
            return self._success(
                "Top customers fetched",
                {
                    "customers": [self._serialize_customer(customer) for customer in customers],
                    "count": len(customers),
                    "limit": safe_limit,
                },
            )
        finally:
            db.close()

    def get_customer_history(self, customer_id: int) -> dict[str, Any]:
        """Return purchase history for one customer ordered from newest to oldest."""
        db = SessionLocal()
        try:
            customer = self._find_customer(db, customer_id=customer_id)
            if not customer:
                return self._error("Customer not found", f"Customer '{customer_id}' does not exist")

            history_rows = (
                db.query(CustomerPurchaseHistory)
                .filter(CustomerPurchaseHistory.customer_id == customer_id)
                .order_by(CustomerPurchaseHistory.purchase_date.desc())
                .all()
            )
            return self._success(
                "Customer history fetched",
                {
                    "customer": self._serialize_customer(customer),
                    "history": [self._serialize_history(history_row) for history_row in history_rows],
                    "count": len(history_rows),
                },
            )
        finally:
            db.close()

    def segment_customers(self) -> dict[str, Any]:
        """Recompute recency segments for all customers."""
        db = SessionLocal()
        try:
            customers = db.query(Customer).all()
            counts = {"Active": 0, "Warm": 0, "Inactive": 0}
            changed = 0

            for customer in customers:
                last_purchase_date = customer.last_purchase_date or customer.last_purchase_at
                segment = self._segment_for_date(last_purchase_date)
                if customer.segment != segment:
                    customer.segment = segment
                    changed += 1
                counts[segment] += 1

            db.commit()
            return self._success(
                "Customer segmentation completed",
                {
                    "segments": counts,
                    "customer_count": len(customers),
                    "updated_count": changed,
                },
            )
        except Exception as exc:
            db.rollback()
            return self._error("Customer segmentation failed", str(exc))
        finally:
            db.close()

    def get_inactive_customers(self, days: int = DEFAULT_INACTIVE_DAYS) -> dict[str, Any]:
        """Return customers whose last purchase is older than the supplied threshold."""
        safe_days = max(int(days or DEFAULT_INACTIVE_DAYS), 1)
        cutoff = datetime.utcnow() - timedelta(days=safe_days)
        db = SessionLocal()
        try:
            customers = db.query(Customer).order_by(Customer.last_purchase_date.asc()).all()
            inactive_customers = [
                self._serialize_customer(customer)
                for customer in customers
                if (customer.last_purchase_date or customer.last_purchase_at) is None
                or (customer.last_purchase_date or customer.last_purchase_at) < cutoff
            ]
            return self._success(
                "Inactive customer scan completed",
                {
                    "customers": inactive_customers,
                    "count": len(inactive_customers),
                    "days": safe_days,
                },
            )
        finally:
            db.close()

    def suggest_campaign(
        self,
        days: int = DEFAULT_INACTIVE_DAYS,
        discount_percentage: int = DEFAULT_DISCOUNT_PERCENTAGE,
    ) -> dict[str, Any]:
        """Generate a simple win-back campaign suggestion for inactive customers."""
        inactive_result = self.get_inactive_customers(days=days)
        if not inactive_result["success"]:
            return inactive_result

        inactive_customers = inactive_result["data"]["customers"]
        contactable_customers = [
            customer for customer in inactive_customers if self._is_contactable_phone(customer["phone"])
        ]

        campaign = {
            "name": f"win-back-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "segment": "Inactive",
            "audience_days": max(int(days or DEFAULT_INACTIVE_DAYS), 1),
            "discount_percentage": max(int(discount_percentage or DEFAULT_DISCOUNT_PERCENTAGE), 1),
            "message": (
                f"We miss you. Enjoy {max(int(discount_percentage or DEFAULT_DISCOUNT_PERCENTAGE), 1)}% off "
                "on your next purchase. Reply to this message to claim the offer."
            ),
            "customer_ids": [customer["id"] for customer in contactable_customers],
            "customers": contactable_customers,
            "recipient_count": len(contactable_customers),
        }

        message = (
            "Campaign suggestion generated"
            if contactable_customers
            else "Inactive customers found, but no contactable WhatsApp recipients are available"
        )
        return self._success(message, {"campaign": campaign, "inactive_customer_count": len(inactive_customers)})

    async def _request_campaign_approval(self, task_id: str, campaign: dict[str, Any]) -> dict[str, Any]:
        """Raise a HITL approval request for a proposed campaign."""
        preview = {
            "title": "CRM Campaign Approval",
            "description": "Send offer to inactive customers",
            "data": campaign,
        }

        tool = TOOL_MAP.get("create_hitl_request", create_hitl_request)
        tool_result = tool.invoke(
            {
                "task_id": task_id,
                "agent_name": self.name,
                "action_type": HITLActionType.WHATSAPP_BROADCAST.value,
                "action_preview": preview,
                "risk_flag": RiskFlag.MEDIUM.value,
            }
        )

        hitl_id = await hitl_gate.create_request(
            task_id=task_id,
            agent_name=self.name,
            action_type=HITLActionType.WHATSAPP_BROADCAST,
            action_preview=preview,
            risk_flag=RiskFlag.MEDIUM,
        )

        await self._broadcast_update(
            task_id,
            "campaign_pending_approval",
            {
                "hitl_id": hitl_id,
                "campaign_name": campaign["name"],
                "recipient_count": campaign["recipient_count"],
            },
        )
        return {"hitl_id": hitl_id, "tool_result": tool_result, "preview": preview}

    def send_campaign(self, campaign: dict[str, Any]) -> dict[str, Any]:
        """Send a campaign via the WhatsApp tool and persist a campaign log."""
        customers = list(campaign.get("customers") or [])
        message = str(campaign.get("message") or "").strip()
        campaign_name = str(campaign.get("name") or f"crm-campaign-{uuid.uuid4().hex[:8]}").strip()
        segment = str(campaign.get("segment") or "Inactive").strip()

        if not customers:
            return self._error("Campaign send failed", "Campaign does not include any customers")
        if not message:
            return self._error("Campaign send failed", "Campaign message is required")

        whatsapp_tool = TOOL_MAP.get("send_whatsapp", send_whatsapp)
        delivery_results: list[dict[str, Any]] = []
        sent_count = 0

        for customer in customers:
            phone = str(customer.get("phone") or "").strip()
            if not self._is_contactable_phone(phone):
                delivery_results.append(
                    {
                        "customer_id": customer.get("id"),
                        "phone": phone,
                        "success": False,
                        "error": "Customer phone is not contactable",
                    }
                )
                continue

            result = whatsapp_tool.invoke({"phone_number": phone, "message": message})
            sent_count += int(bool(result.get("success")))
            delivery_results.append(
                {
                    "customer_id": customer.get("id"),
                    "phone": phone,
                    "success": bool(result.get("success")),
                    "result": result,
                }
            )

        db = SessionLocal()
        try:
            db.add(
                CampaignLog(
                    campaign_name=campaign_name,
                    segment=segment,
                    message_template=message,
                    sent_count=sent_count,
                    delivered_count=sent_count,
                    read_count=0,
                    reply_count=0,
                    created_at=datetime.utcnow(),
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        return self._success(
            "Campaign send attempted",
            {
                "campaign_name": campaign_name,
                "segment": segment,
                "recipient_count": len(customers),
                "sent_count": sent_count,
                "failed_count": len(customers) - sent_count,
                "results": delivery_results,
            },
        )

    async def _handle_billing_event(self, task_id: str, event: dict[str, Any]) -> dict[str, Any]:
        """Process invoice-created billing events and sync customer intelligence."""
        payload = event.get("payload", {}) or {}
        action = str(payload.get("action", "")).lower()
        if action != "invoice_created":
            return self._error(
                "Unsupported billing action",
                f"CRMAgent cannot handle billing action '{action}'",
                {"action": action},
            )

        customer_data = self._extract_customer_payload(payload)
        if not any(customer_data.get(key) for key in ("name", "phone", "email", "gstin")):
            return self._error(
                "Missing customer data",
                "Billing event payload must include customer identifiers",
            )

        items = list(payload.get("items") or payload.get("line_items") or [])
        total = self._coerce_float(payload.get("total"))
        purchase_date = self._resolve_purchase_date(payload, event.get("timestamp"))
        invoice_reference = str(
            payload.get("invoice_number") or payload.get("invoice_id") or payload.get("invoice_reference") or ""
        ).strip() or None

        self._log_step(
            task_id,
            "action",
            f"Syncing CRM customer for billing event invoice_reference={invoice_reference or 'n/a'}.",
        )

        customer, history_row, created = self._upsert_customer_purchase(
            event_id=str(event.get("id") or "").strip() or None,
            source=str(event.get("source") or "billing"),
            invoice_reference=invoice_reference,
            customer_data=customer_data,
            items=items,
            total=total,
            purchase_date=purchase_date,
            event_payload=payload,
        )

        await self._broadcast_update(
            task_id,
            "customer_synced",
            {
                "customer_id": customer.id,
                "customer_name": customer.name,
                "invoice_reference": invoice_reference,
                "created": created,
            },
        )

        message = "Customer created and synced from billing event" if created else "Customer synced from billing event"
        if history_row and history_row.source_event_id == str(event.get("id") or "").strip():
            message = f"{message}; purchase history updated"

        return self._success(
            message,
            {
                "customer": self._serialize_customer(customer),
                "purchase_history": self._serialize_history(history_row) if history_row else None,
            },
        )

    async def _handle_query_event(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle CRM queries and lightweight management actions."""
        action = str(payload.get("action", "")).lower()
        query_text = str(
            payload.get("query") or payload.get("message") or payload.get("text") or ""
        ).lower()

        if action in {"create_customer"}:
            return self.create_customer(
                name=str(payload.get("name") or ""),
                phone=str(payload.get("phone") or ""),
                email=payload.get("email"),
                gstin=payload.get("gstin"),
            )

        if action in {"update_customer"}:
            customer_id = payload.get("customer_id")
            if customer_id in (None, ""):
                return self._error("Customer update failed", "customer_id is required")
            updates = {key: value for key, value in payload.items() if key != "customer_id"}
            return self.update_customer(int(customer_id), **updates)

        if action in {"show_customers", "list_customers"} or "show customers" in query_text:
            return self.list_customers()

        if action in {"top_customers"} or "top customers" in query_text:
            return self.top_customers(limit=int(payload.get("limit", 5)))

        if action in {"inactive_customers"} or "inactive customers" in query_text:
            return self.get_inactive_customers(days=int(payload.get("days", DEFAULT_INACTIVE_DAYS)))

        if action in {"segment_customers", "customer_segmentation"} or "segment" in query_text:
            return self.segment_customers()

        if action in {"suggest_campaign", "campaign_suggestion"} or "campaign" in query_text:
            return await self._handle_campaign_suggestion(task_id, payload)

        if action in {"customer_history"} or "customer history" in query_text or "history" in query_text:
            db = SessionLocal()
            try:
                customer = self._get_customer_by_identifier(db, payload)
                if not customer:
                    return self._error(
                        "Customer history lookup failed",
                        "Provide customer_id, phone, email, gstin, or name for history lookup",
                    )
                return self.get_customer_history(customer.id)
            finally:
                db.close()

        return self._error(
            "Unsupported CRM query",
            "Supported queries: show customers, top customers, inactive customers, customer history, segment customers, suggest campaign",
            {"action": action, "query": query_text},
        )

    async def _handle_campaign_suggestion(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate a campaign and raise a HITL approval request when needed."""
        suggestion = self.suggest_campaign(
            days=int(payload.get("days", DEFAULT_INACTIVE_DAYS)),
            discount_percentage=int(payload.get("discount_percentage", DEFAULT_DISCOUNT_PERCENTAGE)),
        )
        if not suggestion["success"]:
            return suggestion

        campaign = suggestion["data"]["campaign"]
        if not campaign["recipient_count"]:
            return suggestion

        approval = await self._request_campaign_approval(task_id, campaign)
        return self._success(
            "Campaign suggestion generated and sent for approval",
            {
                **suggestion["data"],
                "hitl_request": approval,
            },
            hitl_required=True,
            hitl_id=approval["hitl_id"],
        )

    async def _handle_send_campaign(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send an already-approved or manually-triggered campaign."""
        campaign = payload.get("campaign")
        if not isinstance(campaign, dict):
            suggestion = self.suggest_campaign(
                days=int(payload.get("days", DEFAULT_INACTIVE_DAYS)),
                discount_percentage=int(payload.get("discount_percentage", DEFAULT_DISCOUNT_PERCENTAGE)),
            )
            if not suggestion["success"]:
                return suggestion
            campaign = suggestion["data"]["campaign"]

        self._log_step(task_id, "action", f"Sending campaign '{campaign.get('name')}'.")
        result = self.send_campaign(campaign)
        await self._broadcast_update(
            task_id,
            "campaign_send_attempted",
            {
                "campaign_name": campaign.get("name"),
                "sent_count": result["data"].get("sent_count", 0) if result["success"] else 0,
            },
        )
        return result

    async def _handle_scheduler_event(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run scheduled CRM tasks such as segmentation or campaign planning."""
        task_name = str(payload.get("task", payload.get("action", "customer_segmentation"))).lower()
        if task_name in {"customer_segmentation", "segment_customers"}:
            result = self.segment_customers()
            await self._broadcast_update(
                task_id,
                "customer_segmentation_complete",
                result["data"],
            )
            return result
        if task_name in {"campaign_suggestion", "suggest_campaign"}:
            return await self._handle_campaign_suggestion(task_id, payload)
        if task_name in {"inactive_customer_scan", "inactive_customers"}:
            return self.get_inactive_customers(days=int(payload.get("days", DEFAULT_INACTIVE_DAYS)))
        return self._error(
            "Unsupported CRM scheduler task",
            f"Task '{task_name}' is not supported",
            {"task": task_name},
        )

    async def _dispatch_event(
        self,
        task_id: str,
        event: dict[str, Any],
        shared_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Route an incoming event to the appropriate CRM workflow."""
        _ = shared_context
        event_type = str(event.get("type", "")).upper()
        module = str(event.get("module", "")).lower()
        payload = event.get("payload", {}) or {}

        self._log_step(
            task_id,
            "thought",
            f"CRMAgent routing event type='{event_type}' module='{module}'.",
        )

        if module == "billing" or str(payload.get("action", "")).lower() == "invoice_created":
            return await self._handle_billing_event(task_id, event)

        if module == "crm":
            if event_type == "QUERY":
                return await self._handle_query_event(task_id, payload)
            if event_type in {"EVENT", "SCHEDULED_CHECK"}:
                return await self._handle_scheduler_event(task_id, payload)
            if event_type == "ACTION":
                action = str(payload.get("action", "")).lower()
                if action in {"send_campaign", "execute_campaign"}:
                    return await self._handle_send_campaign(task_id, payload)
                return await self._handle_query_event(task_id, payload)

        return self._error(
            "Unsupported CRM event",
            f"Cannot handle event type '{event_type}' for module '{module}'",
            {"event_type": event_type, "module": module},
        )

    async def run(self, task_id: str, event: dict[str, Any], shared_context: dict[str, Any]) -> dict[str, Any]:
        """Run the CRM agent inside the orchestrator async contract."""
        try:
            return await self._dispatch_event(task_id, event, shared_context)
        except Exception as exc:
            logger.error(f"[CRMAgent] Run failed: {exc}")
            return self._error("CRM agent failed", str(exc))

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle a CRM event directly outside the orchestrator async flow."""
        task_id = str(event.get("id") or f"crm-{uuid.uuid4().hex[:8]}")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._dispatch_event(task_id, event, {}))
        return self._error(
            "Direct handle_event unavailable in running event loop",
            "Use 'await crm_agent.run(task_id, event, shared_context)' inside async contexts",
        )


crm_agent = CRMAgent()
AGENT_REGISTRY["crm_agent"] = crm_agent
AGENT_REGISTRY["crm"] = crm_agent.handle_event
logger.info("[CRMAgent] Registered in AGENT_REGISTRY")


def handle_event(event: dict[str, Any]) -> dict[str, Any]:
    """Handle a CRM event through the module-level direct entry point."""
    return crm_agent.handle_event(event)
