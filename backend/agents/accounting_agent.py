"""Accounting agent implementation for MSME revenue analytics workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, text

from agents.memory import memory_store
from agents.orchestrator import AGENT_REGISTRY
from core.db import InventoryItem, Invoice, SessionLocal, Transaction, get_engine, init_db

logger = logging.getLogger(__name__)

DEFAULT_COST_RATIO = 0.6
DEFAULT_TREND_DAYS = 30


class AccountingAgent:
    """Track revenue, compute P&L, and serve accounting analytics."""

    def __init__(self) -> None:
        """Initialise the accounting agent and ensure analytics schema exists."""
        init_db()
        self.name = "accounting_agent"
        self.default_cost_ratio = self._coerce_float(
            os.getenv("ACCOUNTING_DEFAULT_COST_RATIO"),
            DEFAULT_COST_RATIO,
        )
        self._ensure_schema()
        logger.info("[AccountingAgent] Initialised")

    def _ensure_schema(self) -> None:
        """Create optional analytics tables required for KPI and product insights."""
        engine = get_engine()
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS product_sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_event_id VARCHAR(64),
                        invoice_reference VARCHAR(64),
                        product_key VARCHAR(128) NOT NULL,
                        product_name VARCHAR(255) NOT NULL,
                        quantity FLOAT NOT NULL DEFAULT 0.0,
                        revenue FLOAT NOT NULL DEFAULT 0.0,
                        sold_at DATETIME NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_product_sales_sold_at
                    ON product_sales(sold_at)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_product_sales_event
                    ON product_sales(source_event_id)
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

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        """Convert a value to float and return a default on invalid input."""
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _parse_datetime(
        self,
        value: Any,
        *,
        default: datetime | None = None,
        end_of_day: bool = False,
    ) -> datetime:
        """Parse flexible date/time payloads into UTC-naive datetime objects."""
        fallback = default or datetime.utcnow()
        if value in (None, ""):
            return fallback
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.utcfromtimestamp(float(value))
            except (TypeError, ValueError, OSError):
                return fallback

        raw = str(value).strip()
        if not raw:
            return fallback

        normalized = raw.replace("Z", "+00:00")
        parsed: datetime | None = None
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            pass

        if not parsed:
            for date_format in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
            ):
                try:
                    parsed = datetime.strptime(raw, date_format)
                    break
                except ValueError:
                    continue

        if not parsed:
            return fallback

        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)

        if end_of_day and len(raw) == 10 and "-" in raw:
            return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed

    def _month_range(self, month: str | None = None) -> tuple[datetime, datetime]:
        """Build a start/end datetime range for a supplied month string."""
        if month and len(month.strip()) >= 7:
            start = self._parse_datetime(f"{month.strip()[:7]}-01", default=datetime.utcnow())
        else:
            now = datetime.utcnow()
            start = datetime(now.year, now.month, 1)
        if start.month == 12:
            next_month = datetime(start.year + 1, 1, 1)
        else:
            next_month = datetime(start.year, start.month + 1, 1)
        end = next_month - timedelta(microseconds=1)
        return start, end

    def _extract_line_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalise billing item payloads into a predictable item list."""
        raw_items = payload.get("items") or payload.get("line_items") or []
        if not isinstance(raw_items, list):
            return []
        return [item for item in raw_items if isinstance(item, dict)]

    def _normalize_product_metrics(self, item: dict[str, Any]) -> tuple[str, str, float, float]:
        """Resolve product key/name, quantity, and line revenue for analytics."""
        product_name = str(
            item.get("name") or item.get("description") or item.get("product_name") or "Unknown Product"
        ).strip()
        sku = str(item.get("sku") or item.get("product_id") or "").strip()
        product_key = sku or product_name.lower()
        quantity = self._coerce_float(item.get("quantity", item.get("qty", 0.0)), 0.0)
        unit_price = self._coerce_float(
            item.get("unit_price", item.get("price", item.get("rate", 0.0))),
            0.0,
        )
        line_revenue = self._coerce_float(
            item.get("line_total", item.get("total", item.get("amount", 0.0))),
            0.0,
        )
        if line_revenue <= 0.0 and quantity > 0.0 and unit_price > 0.0:
            line_revenue = quantity * unit_price
        return product_key, product_name, quantity, line_revenue

    def _record_product_sales(
        self,
        items: list[dict[str, Any]],
        *,
        source_event_id: str | None,
        invoice_reference: str | None,
        sold_at: datetime,
    ) -> dict[str, Any]:
        """Persist product-level sales analytics for top-product queries."""
        if not items:
            return {"inserted_count": 0, "duplicate_event": False}

        engine = get_engine()
        with engine.begin() as connection:
            if source_event_id:
                existing = connection.execute(
                    text(
                        """
                        SELECT 1
                        FROM product_sales
                        WHERE source_event_id = :source_event_id
                        LIMIT 1
                        """
                    ),
                    {"source_event_id": source_event_id},
                ).first()
                if existing:
                    return {"inserted_count": 0, "duplicate_event": True}

            aggregated: dict[str, dict[str, Any]] = {}
            for item in items:
                product_key, product_name, quantity, revenue = self._normalize_product_metrics(item)
                if quantity <= 0.0 and revenue <= 0.0:
                    continue
                if product_key not in aggregated:
                    aggregated[product_key] = {
                        "product_name": product_name,
                        "quantity": 0.0,
                        "revenue": 0.0,
                    }
                aggregated[product_key]["quantity"] += quantity
                aggregated[product_key]["revenue"] += revenue

            inserted_count = 0
            for product_key, stats in aggregated.items():
                connection.execute(
                    text(
                        """
                        INSERT INTO product_sales (
                            source_event_id,
                            invoice_reference,
                            product_key,
                            product_name,
                            quantity,
                            revenue,
                            sold_at,
                            created_at
                        ) VALUES (
                            :source_event_id,
                            :invoice_reference,
                            :product_key,
                            :product_name,
                            :quantity,
                            :revenue,
                            :sold_at,
                            :created_at
                        )
                        """
                    ),
                    {
                        "source_event_id": source_event_id,
                        "invoice_reference": invoice_reference,
                        "product_key": product_key,
                        "product_name": stats["product_name"],
                        "quantity": float(stats["quantity"]),
                        "revenue": float(stats["revenue"]),
                        "sold_at": sold_at,
                        "created_at": datetime.utcnow(),
                    },
                )
                inserted_count += 1

        return {"inserted_count": inserted_count, "duplicate_event": False}

    def record_revenue(
        self,
        amount: float,
        timestamp: str,
        *,
        source_event_id: str | None = None,
        invoice_reference: str | None = None,
    ) -> dict[str, Any]:
        """Record invoice revenue into the transactions ledger."""
        clean_amount = self._coerce_float(amount, 0.0)
        if clean_amount <= 0.0:
            return self._error(
                "Revenue recording failed",
                "Revenue amount must be greater than zero",
                {"amount": clean_amount},
            )

        txn_date = self._parse_datetime(timestamp, default=datetime.utcnow())
        db = SessionLocal()
        try:
            if source_event_id:
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.txn_type == "revenue",
                        Transaction.bank_ref == source_event_id,
                    )
                    .first()
                )
                if existing:
                    return self._success(
                        "Revenue already recorded for this event",
                        {
                            "transaction_id": existing.id,
                            "amount": float(existing.amount),
                            "timestamp": existing.txn_date.isoformat(),
                            "already_exists": True,
                        },
                    )

            transaction = Transaction(
                txn_date=txn_date,
                description=f"Invoice revenue {invoice_reference or ''}".strip(),
                amount=clean_amount,
                txn_type="revenue",
                category="invoice",
                bank_ref=source_event_id,
                tally_ref=invoice_reference,
                reconciled=False,
                created_at=datetime.utcnow(),
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)

            return self._success(
                "Revenue recorded successfully",
                {
                    "transaction_id": transaction.id,
                    "amount": float(transaction.amount),
                    "timestamp": transaction.txn_date.isoformat(),
                    "already_exists": False,
                },
            )
        except Exception as exc:
            db.rollback()
            return self._error("Revenue recording failed", str(exc))
        finally:
            db.close()

    def get_total_revenue(self) -> float:
        """Return total tracked revenue amount."""
        db = SessionLocal()
        try:
            total = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(Transaction.txn_type == "revenue")
                .scalar()
                or 0.0
            )
            return round(float(total), 2)
        finally:
            db.close()

    def get_revenue_by_date_range(self, start: str, end: str) -> dict[str, Any]:
        """Return total revenue for a supplied start/end datetime range."""
        start_dt = self._parse_datetime(start, default=datetime.utcnow())
        end_dt = self._parse_datetime(end, default=datetime.utcnow(), end_of_day=True)
        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt

        db = SessionLocal()
        try:
            total = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(
                    Transaction.txn_type == "revenue",
                    Transaction.txn_date >= start_dt,
                    Transaction.txn_date <= end_dt,
                )
                .scalar()
                or 0.0
            )
            invoice_count = (
                db.query(func.count(Transaction.id))
                .filter(
                    Transaction.txn_type == "revenue",
                    Transaction.txn_date >= start_dt,
                    Transaction.txn_date <= end_dt,
                )
                .scalar()
                or 0
            )
            return {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "total_revenue": round(float(total), 2),
                "invoice_count": int(invoice_count),
            }
        finally:
            db.close()

    def _get_top_products_from_product_sales(
        self,
        *,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Query top-selling products from the product_sales analytics table."""
        limit_value = max(int(limit or 5), 1)
        engine = get_engine()
        sql = """
            SELECT
                product_key,
                product_name,
                SUM(quantity) AS quantity_sold,
                SUM(revenue) AS revenue
            FROM product_sales
            WHERE (:start_dt IS NULL OR sold_at >= :start_dt)
              AND (:end_dt IS NULL OR sold_at <= :end_dt)
            GROUP BY product_key, product_name
            ORDER BY quantity_sold DESC, revenue DESC
            LIMIT :limit_value
        """
        with engine.connect() as connection:
            rows = connection.execute(
                text(sql),
                {
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "limit_value": limit_value,
                },
            ).mappings().all()
        return [
            {
                "product_key": str(row["product_key"]),
                "product_name": str(row["product_name"]),
                "quantity_sold": round(self._coerce_float(row["quantity_sold"]), 2),
                "revenue": round(self._coerce_float(row["revenue"]), 2),
            }
            for row in rows
        ]

    def _get_top_products_from_invoices(
        self,
        *,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Fallback top-product computation by parsing invoice line items."""
        db = SessionLocal()
        try:
            query = db.query(Invoice)
            if start_dt:
                query = query.filter(Invoice.created_at >= start_dt)
            if end_dt:
                query = query.filter(Invoice.created_at <= end_dt)
            invoices = query.all()
        finally:
            db.close()

        aggregate: dict[str, dict[str, float | str]] = {}
        for invoice in invoices:
            try:
                items = json.loads(invoice.line_items)
            except (TypeError, ValueError):
                items = []
            if not isinstance(items, list):
                continue
            for raw_item in items:
                if not isinstance(raw_item, dict):
                    continue
                product_key, product_name, quantity, revenue = self._normalize_product_metrics(raw_item)
                if quantity <= 0.0 and revenue <= 0.0:
                    continue
                if product_key not in aggregate:
                    aggregate[product_key] = {
                        "product_name": product_name,
                        "quantity_sold": 0.0,
                        "revenue": 0.0,
                    }
                aggregate[product_key]["quantity_sold"] = (
                    self._coerce_float(aggregate[product_key]["quantity_sold"]) + quantity
                )
                aggregate[product_key]["revenue"] = self._coerce_float(aggregate[product_key]["revenue"]) + revenue

        ranked = sorted(
            [
                {
                    "product_key": key,
                    "product_name": str(values["product_name"]),
                    "quantity_sold": round(self._coerce_float(values["quantity_sold"]), 2),
                    "revenue": round(self._coerce_float(values["revenue"]), 2),
                }
                for key, values in aggregate.items()
            ],
            key=lambda row: (row["quantity_sold"], row["revenue"]),
            reverse=True,
        )
        return ranked[: max(int(limit or 5), 1)]

    def get_top_selling_products(
        self,
        limit: int = 5,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top-selling products using billing-derived item data."""
        start_dt = self._parse_datetime(start, default=None) if start else None
        end_dt = self._parse_datetime(end, default=None, end_of_day=True) if end else None
        top_products = self._get_top_products_from_product_sales(
            start_dt=start_dt,
            end_dt=end_dt,
            limit=limit,
        )
        if top_products:
            return top_products
        return self._get_top_products_from_invoices(
            start_dt=start_dt,
            end_dt=end_dt,
            limit=limit,
        )

    def _estimate_cost_from_invoices(
        self,
        *,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> dict[str, Any]:
        """Estimate COGS from invoice items using inventory cost when available."""
        db = SessionLocal()
        try:
            inventory_rows = db.query(InventoryItem).all()
            inventory_by_sku = {
                str(row.sku).strip().lower(): self._coerce_float(row.cost_price)
                for row in inventory_rows
                if row.cost_price is not None and str(row.sku).strip()
            }
            inventory_by_name = {
                str(row.name).strip().lower(): self._coerce_float(row.cost_price)
                for row in inventory_rows
                if row.cost_price is not None and str(row.name).strip()
            }

            query = db.query(Invoice)
            if start_dt:
                query = query.filter(Invoice.created_at >= start_dt)
            if end_dt:
                query = query.filter(Invoice.created_at <= end_dt)
            invoices = query.all()
        finally:
            db.close()

        estimated_cost = 0.0
        inventory_priced_items = 0
        fallback_priced_items = 0

        for invoice in invoices:
            try:
                items = json.loads(invoice.line_items)
            except (TypeError, ValueError):
                items = []
            if not isinstance(items, list):
                continue

            for raw_item in items:
                if not isinstance(raw_item, dict):
                    continue

                quantity = self._coerce_float(raw_item.get("quantity", raw_item.get("qty", 0.0)), 0.0)
                unit_price = self._coerce_float(
                    raw_item.get("unit_price", raw_item.get("price", raw_item.get("rate", 0.0))),
                    0.0,
                )
                line_total = self._coerce_float(
                    raw_item.get("line_total", raw_item.get("total", raw_item.get("amount", 0.0))),
                    0.0,
                )
                if quantity <= 0.0 and unit_price > 0.0 and line_total > 0.0:
                    quantity = line_total / unit_price

                explicit_cost = self._coerce_float(raw_item.get("cost_price"), 0.0)
                if explicit_cost > 0.0 and quantity > 0.0:
                    estimated_cost += explicit_cost * quantity
                    inventory_priced_items += 1
                    continue

                sku = str(raw_item.get("sku", "")).strip().lower()
                name = str(
                    raw_item.get("name") or raw_item.get("description") or raw_item.get("product_name") or ""
                ).strip().lower()
                inventory_cost = 0.0
                if sku:
                    inventory_cost = self._coerce_float(inventory_by_sku.get(sku), 0.0)
                if inventory_cost <= 0.0 and name:
                    inventory_cost = self._coerce_float(inventory_by_name.get(name), 0.0)

                if inventory_cost > 0.0 and quantity > 0.0:
                    estimated_cost += inventory_cost * quantity
                    inventory_priced_items += 1
                    continue

                fallback_base = line_total if line_total > 0.0 else (quantity * unit_price)
                if fallback_base > 0.0:
                    estimated_cost += fallback_base * self.default_cost_ratio
                    fallback_priced_items += 1

        return {
            "estimated_cost": round(estimated_cost, 2),
            "inventory_priced_items": inventory_priced_items,
            "fallback_priced_items": fallback_priced_items,
        }

    def calculate_profit(self, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        """Compute a simple profit estimate as revenue minus estimated cost."""
        start_dt = self._parse_datetime(start, default=None) if start else None
        end_dt = self._parse_datetime(end, default=None, end_of_day=True) if end else None

        if start_dt and end_dt and start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt

        if start_dt and end_dt:
            revenue_data = self.get_revenue_by_date_range(start_dt.isoformat(), end_dt.isoformat())
            total_revenue = self._coerce_float(revenue_data["total_revenue"], 0.0)
            invoice_count = int(revenue_data["invoice_count"])
        else:
            total_revenue = self.get_total_revenue()
            db = SessionLocal()
            try:
                invoice_count = (
                    db.query(func.count(Transaction.id))
                    .filter(Transaction.txn_type == "revenue")
                    .scalar()
                    or 0
                )
            finally:
                db.close()

        cost_data = self._estimate_cost_from_invoices(start_dt=start_dt, end_dt=end_dt)
        estimated_cost = self._coerce_float(cost_data["estimated_cost"], 0.0)
        if total_revenue > 0.0 and estimated_cost <= 0.0:
            estimated_cost = round(total_revenue * self.default_cost_ratio, 2)

        profit = round(total_revenue - estimated_cost, 2)
        profit_margin = round((profit / total_revenue) * 100, 2) if total_revenue > 0.0 else 0.0

        return {
            "total_revenue": round(total_revenue, 2),
            "estimated_cost": round(estimated_cost, 2),
            "profit": profit,
            "profit_margin_percent": profit_margin,
            "invoice_count": int(invoice_count),
            "costing": {
                "inventory_priced_items": int(cost_data["inventory_priced_items"]),
                "fallback_priced_items": int(cost_data["fallback_priced_items"]),
                "default_cost_ratio": self.default_cost_ratio,
            },
            "range": {
                "start": start_dt.isoformat() if start_dt else None,
                "end": end_dt.isoformat() if end_dt else None,
            },
        }

    def get_kpis(self) -> dict[str, Any]:
        """Return dashboard KPI cards for revenue, invoice count, and top product."""
        total_revenue = self.get_total_revenue()
        db = SessionLocal()
        try:
            total_invoices = (
                db.query(func.count(Transaction.id))
                .filter(Transaction.txn_type == "revenue")
                .scalar()
                or 0
            )
        finally:
            db.close()

        avg_order_value = round(total_revenue / total_invoices, 2) if total_invoices else 0.0
        top_product = self.get_top_selling_products(limit=1)

        return {
            "total_revenue": round(total_revenue, 2),
            "total_invoices": int(total_invoices),
            "avg_order_value": avg_order_value,
            "top_product": top_product[0] if top_product else None,
        }

    def get_revenue_trend(
        self,
        granularity: str = "daily",
        start: str | None = None,
        end: str | None = None,
        days: int = DEFAULT_TREND_DAYS,
    ) -> dict[str, Any]:
        """Return time-series revenue aggregates grouped by day or week."""
        safe_granularity = str(granularity or "daily").lower()
        if safe_granularity not in {"daily", "weekly", "monthly"}:
            safe_granularity = "daily"

        end_dt = self._parse_datetime(end, default=datetime.utcnow(), end_of_day=True) if end else datetime.utcnow()
        start_dt = (
            self._parse_datetime(start, default=end_dt - timedelta(days=max(int(days), 1)))
            if start
            else (end_dt - timedelta(days=max(int(days or DEFAULT_TREND_DAYS), 1)))
        )
        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt

        period_format = {
            "daily": "%Y-%m-%d",
            "weekly": "%Y-W%W",
            "monthly": "%Y-%m",
        }[safe_granularity]

        db = SessionLocal()
        try:
            period_expr = func.strftime(period_format, Transaction.txn_date)
            rows = (
                db.query(
                    period_expr.label("period"),
                    func.coalesce(func.sum(Transaction.amount), 0.0).label("revenue"),
                    func.count(Transaction.id).label("invoice_count"),
                )
                .filter(
                    Transaction.txn_type == "revenue",
                    Transaction.txn_date >= start_dt,
                    Transaction.txn_date <= end_dt,
                )
                .group_by(period_expr)
                .order_by(period_expr.asc())
                .all()
            )
        finally:
            db.close()

        points = [
            {
                "period": str(row.period),
                "revenue": round(self._coerce_float(row.revenue), 2),
                "invoice_count": int(row.invoice_count or 0),
            }
            for row in rows
            if row.period is not None
        ]
        return {
            "granularity": safe_granularity,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "points": points,
        }

    def get_receivables_snapshot(self) -> dict[str, Any]:
        """Return a simple AR aging snapshot for scheduled accounting checks."""
        db = SessionLocal()
        try:
            invoices = db.query(Invoice).filter(Invoice.status.in_(["sent", "overdue"])).all()
        finally:
            db.close()

        now = datetime.utcnow()
        buckets = {"0_30": 0.0, "31_60": 0.0, "61_plus": 0.0}
        outstanding_count = 0

        for invoice in invoices:
            age_days = max((now - invoice.created_at).days, 0) if invoice.created_at else 0
            amount = self._coerce_float(invoice.total, 0.0)
            outstanding_count += 1
            if age_days <= 30:
                buckets["0_30"] += amount
            elif age_days <= 60:
                buckets["31_60"] += amount
            else:
                buckets["61_plus"] += amount

        return {
            "outstanding_invoice_count": outstanding_count,
            "total_outstanding": round(sum(buckets.values()), 2),
            "aging_buckets": {key: round(value, 2) for key, value in buckets.items()},
        }

    def get_gstr_prep_summary(self, month: str | None = None) -> dict[str, Any]:
        """Return monthly GST-ready invoice totals for scheduler consumption."""
        start_dt, end_dt = self._month_range(month)
        db = SessionLocal()
        try:
            invoices = (
                db.query(Invoice)
                .filter(
                    Invoice.created_at >= start_dt,
                    Invoice.created_at <= end_dt,
                    Invoice.status.in_(["sent", "paid", "overdue", "draft"]),
                )
                .all()
            )
        finally:
            db.close()

        return {
            "month": start_dt.strftime("%Y-%m"),
            "invoice_count": len(invoices),
            "subtotal": round(sum(self._coerce_float(item.subtotal) for item in invoices), 2),
            "cgst": round(sum(self._coerce_float(item.cgst) for item in invoices), 2),
            "sgst": round(sum(self._coerce_float(item.sgst) for item in invoices), 2),
            "igst": round(sum(self._coerce_float(item.igst) for item in invoices), 2),
            "total": round(sum(self._coerce_float(item.total) for item in invoices), 2),
        }

    async def _handle_billing_event(self, task_id: str, event: dict[str, Any]) -> dict[str, Any]:
        """Process billing invoice-created events and update accounting analytics."""
        payload = event.get("payload", {}) or {}
        action = str(payload.get("action", "")).lower()
        if action != "invoice_created":
            return self._error(
                "Unsupported billing action",
                f"AccountingAgent cannot handle billing action '{action}'",
                {"action": action},
            )

        amount = self._coerce_float(payload.get("total"), 0.0)
        timestamp = str(payload.get("timestamp") or event.get("timestamp") or datetime.utcnow().isoformat())
        source_event_id = str(event.get("id") or "").strip() or None
        invoice_reference = str(
            payload.get("invoice_number") or payload.get("invoice_id") or payload.get("invoice_reference") or ""
        ).strip() or None
        items = self._extract_line_items(payload)

        self._log_step(task_id, "action", f"Recording invoice revenue amount={amount}.")
        revenue_result = self.record_revenue(
            amount=amount,
            timestamp=timestamp,
            source_event_id=source_event_id,
            invoice_reference=invoice_reference,
        )
        if not revenue_result["success"]:
            return revenue_result

        sold_at = self._parse_datetime(timestamp, default=datetime.utcnow())
        product_sales_info = self._record_product_sales(
            items=items,
            source_event_id=source_event_id,
            invoice_reference=invoice_reference,
            sold_at=sold_at,
        )
        kpis = self.get_kpis()

        self._log_step(
            task_id,
            "observation",
            (
                "Revenue persisted and analytics updated. "
                f"transaction_id={revenue_result['data'].get('transaction_id')}"
            ),
        )
        return self._success(
            "Invoice revenue processed successfully",
            {
                "transaction": revenue_result["data"],
                "product_sales": product_sales_info,
                "kpis": kpis,
            },
        )

    async def _handle_query_event(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle accounting metric and insight queries."""
        _ = task_id
        action = str(payload.get("action", "")).lower().strip()
        query_text = str(
            payload.get("query") or payload.get("message") or payload.get("text") or ""
        ).lower().strip()

        if action in {"total_revenue"} or "total revenue" in query_text:
            total_revenue = self.get_total_revenue()
            return self._success("Total revenue fetched", {"total_revenue": total_revenue})

        if action in {"today_revenue"} or "today revenue" in query_text:
            start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            revenue = self.get_revenue_by_date_range(start.isoformat(), datetime.utcnow().isoformat())
            return self._success("Today's revenue fetched", revenue)

        if action in {"monthly_revenue"} or "monthly revenue" in query_text:
            start, end = self._month_range(str(payload.get("month") or "").strip() or None)
            revenue = self.get_revenue_by_date_range(start.isoformat(), end.isoformat())
            return self._success("Monthly revenue fetched", revenue)

        if action in {"top_products", "top_selling_products"} or "top products" in query_text:
            limit = int(payload.get("limit", 5) or 5)
            products = self.get_top_selling_products(
                limit=limit,
                start=payload.get("start"),
                end=payload.get("end"),
            )
            return self._success("Top products fetched", {"products": products, "count": len(products)})

        if action in {"profit", "profit_loss"} or "profit" in query_text:
            profit_data = self.calculate_profit(
                start=payload.get("start"),
                end=payload.get("end"),
            )
            return self._success("Profit metrics fetched", profit_data)

        if action in {"kpis", "get_kpis", "dashboard_kpis"} or "kpi" in query_text:
            return self._success("Accounting KPIs fetched", self.get_kpis())

        if action in {"revenue_trend", "trend"} or "trend" in query_text:
            trend = self.get_revenue_trend(
                granularity=str(payload.get("granularity", "daily")),
                start=payload.get("start"),
                end=payload.get("end"),
                days=int(payload.get("days", DEFAULT_TREND_DAYS) or DEFAULT_TREND_DAYS),
            )
            return self._success("Revenue trend fetched", trend)

        return self._error(
            "Unsupported accounting query",
            (
                "Supported queries: total revenue, today revenue, monthly revenue, "
                "top products, profit, kpis, revenue trend"
            ),
            {"action": action, "query": query_text},
        )

    async def _handle_scheduler_event(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run scheduled accounting tasks."""
        _ = task_id
        task_name = str(payload.get("task", payload.get("action", ""))).lower()

        if task_name in {"ar_aging", "receivables_snapshot"}:
            snapshot = self.get_receivables_snapshot()
            return self._success("AR aging snapshot generated", snapshot)

        if task_name in {"gstr_prep", "gstr_summary"}:
            summary = self.get_gstr_prep_summary(str(payload.get("month") or "").strip() or None)
            return self._success("GSTR prep summary generated", summary)

        if task_name in {"kpi_refresh", "dashboard_refresh"}:
            return self._success(
                "Accounting dashboard metrics refreshed",
                {
                    "kpis": self.get_kpis(),
                    "revenue_trend": self.get_revenue_trend(),
                },
            )

        return self._error(
            "Unsupported accounting scheduler task",
            f"Task '{task_name}' is not supported",
            {"task": task_name},
        )

    async def _dispatch_event(
        self,
        task_id: str,
        event: dict[str, Any],
        shared_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Route incoming events to billing sync, queries, or scheduler handlers."""
        _ = shared_context
        event_type = str(event.get("type", "")).upper()
        module = str(event.get("module", "")).lower()
        payload = event.get("payload", {}) or {}
        action = str(payload.get("action", "")).lower()

        self._log_step(
            task_id,
            "thought",
            f"AccountingAgent routing event type='{event_type}' module='{module}'.",
        )

        if module == "billing" or action == "invoice_created":
            return await self._handle_billing_event(task_id, event)

        if module == "accounting":
            if event_type == "QUERY":
                return await self._handle_query_event(task_id, payload)
            if event_type in {"EVENT", "SCHEDULED_CHECK"}:
                return await self._handle_scheduler_event(task_id, payload)
            if event_type == "ACTION":
                if action == "invoice_created":
                    return await self._handle_billing_event(task_id, event)
                return await self._handle_query_event(task_id, payload)

        return self._error(
            "Unsupported accounting event",
            f"Cannot handle event type '{event_type}' for module '{module}'",
            {"event_type": event_type, "module": module},
        )

    async def run(self, task_id: str, event: dict[str, Any], shared_context: dict[str, Any]) -> dict[str, Any]:
        """Run accounting workflows inside the orchestrator async contract."""
        try:
            return await self._dispatch_event(task_id, event, shared_context)
        except Exception as exc:
            logger.error(f"[AccountingAgent] Run failed: {exc}")
            return self._error("Accounting agent failed", str(exc))

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle accounting events directly outside orchestrator async flow."""
        task_id = str(event.get("id") or f"accounting-{uuid.uuid4().hex[:8]}")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._dispatch_event(task_id, event, {}))
        return self._error(
            "Direct handle_event unavailable in running event loop",
            "Use 'await accounting_agent.run(task_id, event, shared_context)' inside async contexts",
        )


accounting_agent = AccountingAgent()
AGENT_REGISTRY["accounting_agent"] = accounting_agent
AGENT_REGISTRY["accounting"] = accounting_agent.handle_event
logger.info("[AccountingAgent] Registered in AGENT_REGISTRY")


def handle_event(event: dict[str, Any]) -> dict[str, Any]:
    """Handle an accounting event through the module-level direct entry point."""
    return accounting_agent.handle_event(event)
