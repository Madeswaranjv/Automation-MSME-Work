"""Inventory agent implementation for MSME stock workflows."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from agents.hitl import HITLActionType, RiskFlag, hitl_gate
from agents.memory import memory_store
from agents.orchestrator import AGENT_REGISTRY
from agents.tools import TOOL_MAP
from core.db import InventoryItem, SessionLocal, init_db
from core.ws_manager import MessageType, build_ws_message, ws_manager

logger = logging.getLogger(__name__)

DEFAULT_LOW_STOCK_THRESHOLD = 10
REORDER_TARGET_MULTIPLIER = 2


class InventoryAgent:
    """Manage stock levels, invoice deductions, and low-stock reorder alerts."""

    def __init__(self) -> None:
        """Initialise the inventory agent and ensure tables exist."""
        init_db()
        self.name = "inventory_agent"
        logger.info("[InventoryAgent] Initialised")

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

    def _serialize_product(self, product: InventoryItem) -> dict[str, Any]:
        """Convert an InventoryItem row into a structured JSON-friendly dict."""
        return {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "price": float(product.selling_price or 0.0),
            "quantity": float(product.quantity),
            "unit": product.unit,
            "category": product.category,
            "reorder_level": float(product.reorder_level),
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        }

    def _build_reorder_suggestions(
        self,
        products: list[InventoryItem] | list[dict[str, Any]],
        threshold: int = DEFAULT_LOW_STOCK_THRESHOLD,
    ) -> list[dict[str, Any]]:
        """Create simple reorder suggestions for low-stock items."""
        suggestions: list[dict[str, Any]] = []
        for product in products:
            item = self._serialize_product(product) if isinstance(product, InventoryItem) else product
            reorder_level = max(int(item.get("reorder_level", threshold)), threshold)
            current_qty = float(item.get("quantity", 0))
            target_qty = reorder_level * REORDER_TARGET_MULTIPLIER
            suggested_reorder_qty = max(int(round(target_qty - current_qty)), 1)
            suggestions.append(
                {
                    "sku": item["sku"],
                    "name": item["name"],
                    "current_stock": current_qty,
                    "reorder_level": reorder_level,
                    "suggested_reorder_qty": suggested_reorder_qty,
                    "estimated_unit_price": float(item.get("price", 0.0)),
                    "estimated_reorder_value": round(
                        float(item.get("price", 0.0)) * suggested_reorder_qty,
                        2,
                    ),
                }
            )
        return suggestions

    async def _raise_low_stock_alert(
        self,
        task_id: str,
        low_stock_items: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a low-stock HITL approval request and broadcast the alert."""
        preview = {
            "title": "Low Stock Alert",
            "description": f"Reorder needed for {len(suggestions)} SKU(s).",
            "low_stock_items": low_stock_items,
            "reorder_suggestions": suggestions,
            "generated_at": datetime.utcnow().isoformat(),
        }

        tool = TOOL_MAP.get("create_hitl_request")
        tool_result = (
            tool.invoke(
                {
                    "task_id": task_id,
                    "agent_name": self.name,
                    "action_type": HITLActionType.PO_GENERATE.value,
                    "action_preview": preview,
                    "risk_flag": RiskFlag.MEDIUM.value,
                }
            )
            if tool
            else None
        )

        hitl_id = await hitl_gate.create_request(
            task_id=task_id,
            agent_name=self.name,
            action_type=HITLActionType.PO_GENERATE,
            action_preview=preview,
            risk_flag=RiskFlag.MEDIUM,
        )

        await ws_manager.broadcast(
            build_ws_message(
                MessageType.AGENT_UPDATE,
                agent=self.name,
                data={
                    "task_id": task_id,
                    "status": "low_stock_alert",
                    "low_stock_count": len(low_stock_items),
                    "hitl_id": hitl_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
            room="dashboard",
        )
        self._log_step(task_id, "observation", f"Low stock HITL request created: {hitl_id}")
        return {"hitl_id": hitl_id, "tool_result": tool_result}

    def add_product(self, name: str, sku: str, price: float, quantity: int) -> dict[str, Any]:
        """Create a new product record in the inventory store."""
        if not name.strip() or not sku.strip():
            return self._error("Invalid product data", "Both name and sku are required")
        if quantity < 0 or price < 0:
            return self._error("Invalid product data", "Price and quantity must be non-negative")

        db = SessionLocal()
        try:
            existing = db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
            if existing:
                existing.name = name
                existing.selling_price = float(price)
                existing.quantity = float(quantity)
                existing.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing)
                return self._success("Product updated", {"product": self._serialize_product(existing)})

            product = InventoryItem(
                name=name,
                sku=sku,
                selling_price=float(price),
                quantity=float(quantity),
                reorder_level=float(DEFAULT_LOW_STOCK_THRESHOLD),
                updated_at=datetime.utcnow(),
            )
            db.add(product)
            db.commit()
            db.refresh(product)
            return self._success("Product added", {"product": self._serialize_product(product)})
        finally:
            db.close()

    def update_stock(self, sku: str, quantity: int) -> dict[str, Any]:
        """Set the current stock quantity for a SKU."""
        if quantity < 0:
            return self._error("Invalid stock quantity", "Quantity must be non-negative", {"sku": sku})

        db = SessionLocal()
        try:
            product = db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
            if not product:
                return self._error("Product not found", f"SKU '{sku}' does not exist", {"sku": sku})

            product.quantity = float(quantity)
            product.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(product)
            return self._success("Stock updated", {"product": self._serialize_product(product)})
        finally:
            db.close()

    def get_stock(self, sku: str) -> dict[str, Any]:
        """Fetch current stock details for one SKU."""
        db = SessionLocal()
        try:
            product = db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
            if not product:
                return self._error("Product not found", f"SKU '{sku}' does not exist", {"sku": sku})
            return self._success("Stock fetched", {"product": self._serialize_product(product)})
        finally:
            db.close()

    def list_products(self) -> dict[str, Any]:
        """Return all known products sorted by SKU."""
        db = SessionLocal()
        try:
            products = db.query(InventoryItem).order_by(InventoryItem.sku.asc()).all()
            return self._success(
                "Product list fetched",
                {
                    "products": [self._serialize_product(product) for product in products],
                    "count": len(products),
                },
            )
        finally:
            db.close()

    def deduct_stock(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Deduct stock quantities for billed line items."""
        db = SessionLocal()
        try:
            missing: list[dict[str, Any]] = []
            insufficient: list[dict[str, Any]] = []
            updates: list[dict[str, Any]] = []
            loaded_products: list[InventoryItem] = []

            for item in items:
                sku = str(item.get("sku", "")).strip()
                quantity = float(item.get("quantity", 0))
                product = db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
                if not product:
                    missing.append({"sku": sku, "requested_quantity": quantity})
                    continue
                if quantity <= 0:
                    continue
                if product.quantity < quantity:
                    insufficient.append(
                        {
                            "sku": sku,
                            "available_quantity": float(product.quantity),
                            "requested_quantity": quantity,
                        }
                    )
                    continue
                loaded_products.append(product)
                updates.append(
                    {
                        "product": product,
                        "requested_quantity": quantity,
                    }
                )

            if missing or insufficient:
                db.rollback()
                return self._error(
                    "Stock deduction failed",
                    "Missing or insufficient stock prevented invoice deduction",
                    {
                        "missing": missing,
                        "insufficient": insufficient,
                    },
                )

            deducted_items: list[dict[str, Any]] = []
            for update in updates:
                product = update["product"]
                quantity = update["requested_quantity"]
                product.quantity = float(product.quantity) - quantity
                product.updated_at = datetime.utcnow()
                deducted_items.append(
                    {
                        "sku": product.sku,
                        "name": product.name,
                        "deducted_quantity": quantity,
                        "remaining_quantity": float(product.quantity),
                    }
                )

            db.commit()
            return self._success(
                "Stock deducted",
                {
                    "deducted_items": deducted_items,
                    "count": len(deducted_items),
                },
            )
        finally:
            db.close()

    def get_low_stock(self, threshold: int = DEFAULT_LOW_STOCK_THRESHOLD) -> dict[str, Any]:
        """Return all products at or below the supplied threshold or reorder level."""
        db = SessionLocal()
        try:
            products = db.query(InventoryItem).order_by(InventoryItem.quantity.asc()).all()
            low_stock_items = [
                self._serialize_product(product)
                for product in products
                if float(product.quantity) <= max(float(product.reorder_level), float(threshold))
            ]
            return self._success(
                "Low stock scan complete",
                {
                    "items": low_stock_items,
                    "count": len(low_stock_items),
                    "threshold": threshold,
                },
            )
        finally:
            db.close()

    def suggest_reorder(self, threshold: int = DEFAULT_LOW_STOCK_THRESHOLD) -> dict[str, Any]:
        """Generate simple reorder suggestions for low-stock products."""
        low_stock = self.get_low_stock(threshold=threshold)
        if not low_stock["success"]:
            return low_stock
        suggestions = self._build_reorder_suggestions(low_stock["data"]["items"], threshold=threshold)
        return self._success(
            "Reorder suggestions generated",
            {
                "suggestions": suggestions,
                "count": len(suggestions),
                "threshold": threshold,
            },
        )

    async def _handle_billing_event(
        self,
        task_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Process invoice-created billing events and deduct stock."""
        action = str(payload.get("action", "")).lower()
        if action != "invoice_created":
            return self._error(
                "Unsupported billing action",
                f"InventoryAgent cannot handle billing action '{action}'",
                {"action": action},
            )

        items = payload.get("items", [])
        if not items:
            return self._error(
                "Missing billed items",
                "Billing event payload must include a non-empty items list",
            )

        self._log_step(task_id, "action", f"Deducting stock for {len(items)} billed item(s).")
        deduction_result = self.deduct_stock(items)
        if not deduction_result["success"]:
            self._log_step(task_id, "observation", deduction_result["error"])
            return deduction_result

        updated_skus = {str(item.get("sku", "")).strip() for item in items}
        low_stock_scan = self.get_low_stock()
        low_stock_items = [
            item for item in low_stock_scan["data"]["items"] if item["sku"] in updated_skus
        ]
        suggestions = self._build_reorder_suggestions(low_stock_items) if low_stock_items else []

        result: dict[str, Any] = {
            "deduction": deduction_result["data"],
            "low_stock_items": low_stock_items,
            "reorder_suggestions": suggestions,
        }

        if suggestions:
            alert_result = await self._raise_low_stock_alert(task_id, low_stock_items, suggestions)
            result["low_stock_alert"] = alert_result
            return self._success(
                "Invoice stock deducted and low stock alert raised",
                result,
                hitl_required=True,
                hitl_id=alert_result["hitl_id"],
            )

        return self._success("Invoice stock deducted", result)

    async def _handle_query_event(
        self,
        task_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle manual inventory queries and CRUD-style actions."""
        action = str(payload.get("action", "")).lower()
        query_text = str(
            payload.get("query") or payload.get("message") or payload.get("text") or ""
        ).lower()

        if action in {"add_product", "create_product"}:
            return self.add_product(
                name=str(payload.get("name", "")),
                sku=str(payload.get("sku", "")),
                price=float(payload.get("price", 0)),
                quantity=int(payload.get("quantity", 0)),
            )
        if action in {"update_stock", "set_stock"}:
            return self.update_stock(
                sku=str(payload.get("sku", "")),
                quantity=int(payload.get("quantity", 0)),
            )
        if action in {"get_stock", "show_stock"} or "show stock" in query_text or payload.get("sku"):
            sku = str(payload.get("sku", "")).strip()
            if not sku:
                return self.list_products()
            return self.get_stock(sku)
        if action in {"low_stock", "low_stock_items"} or "low stock" in query_text:
            return self.get_low_stock(int(payload.get("threshold", DEFAULT_LOW_STOCK_THRESHOLD)))
        if action in {"list_products", "product_list"} or "product list" in query_text:
            return self.list_products()
        if action in {"suggest_reorder", "reorder"} or "reorder" in query_text:
            return self.suggest_reorder(int(payload.get("threshold", DEFAULT_LOW_STOCK_THRESHOLD)))

        self._log_step(task_id, "observation", f"Unsupported inventory query: action={action}")
        return self._error(
            "Unsupported inventory query",
            "Supported queries: show_stock, low_stock, product_list, suggest_reorder, add_product, update_stock",
            {"action": action, "query": query_text},
        )

    async def _handle_scheduler_event(
        self,
        task_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Run scheduled low-stock scans and reorder suggestion generation."""
        task_name = str(payload.get("task", payload.get("action", "stock_check"))).lower()
        threshold = int(payload.get("threshold", DEFAULT_LOW_STOCK_THRESHOLD))
        if task_name not in {
            "daily_stock_check",
            "forecast_trigger",
            "stock_check",
            "low_stock_check",
            "suggest_reorder",
        }:
            return self._error(
                "Unsupported inventory scheduler task",
                f"Task '{task_name}' is not supported",
                {"task": task_name},
            )

        self._log_step(task_id, "action", f"Running scheduled inventory task '{task_name}'.")
        low_stock = self.get_low_stock(threshold=threshold)
        suggestions_result = self.suggest_reorder(threshold=threshold)
        suggestions = suggestions_result["data"]["suggestions"]

        response_data = {
            "low_stock_items": low_stock["data"]["items"],
            "reorder_suggestions": suggestions,
            "threshold": threshold,
            "task": task_name,
        }

        if suggestions:
            alert_result = await self._raise_low_stock_alert(
                task_id,
                low_stock["data"]["items"],
                suggestions,
            )
            response_data["low_stock_alert"] = alert_result
            return self._success(
                f"Scheduled inventory check complete. {len(suggestions)} reorder suggestion(s) generated.",
                response_data,
                hitl_required=True,
                hitl_id=alert_result["hitl_id"],
            )

        return self._success("Scheduled inventory check complete. No low stock items found.", response_data)

    async def _dispatch_event(
        self,
        task_id: str,
        event: dict[str, Any],
        shared_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Route an incoming event to the appropriate inventory workflow."""
        _ = shared_context
        event_type = str(event.get("type", "")).upper()
        module = str(event.get("module", "")).lower()
        payload = event.get("payload", {}) or {}

        self._log_step(
            task_id,
            "thought",
            f"InventoryAgent routing event type='{event_type}' module='{module}'.",
        )

        if module == "billing" or payload.get("action") == "invoice_created":
            return await self._handle_billing_event(task_id, payload)

        if module == "inventory":
            if event_type == "QUERY":
                return await self._handle_query_event(task_id, payload)
            if event_type in {"EVENT", "SCHEDULED_CHECK"}:
                return await self._handle_scheduler_event(task_id, payload)
            if event_type == "ACTION":
                if str(payload.get("action", "")).lower() == "invoice_created":
                    return await self._handle_billing_event(task_id, payload)
                return await self._handle_query_event(task_id, payload)

        return self._error(
            "Unsupported inventory event",
            f"Cannot handle event type '{event_type}' for module '{module}'",
            {"event_type": event_type, "module": module},
        )

    async def run(self, task_id: str, event: dict[str, Any], shared_context: dict[str, Any]) -> dict[str, Any]:
        """Run the inventory agent inside the orchestrator async contract."""
        try:
            return await self._dispatch_event(task_id, event, shared_context)
        except Exception as exc:
            logger.error(f"[InventoryAgent] Run failed: {exc}")
            return self._error("Inventory agent failed", str(exc))

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle an inventory event directly outside the orchestrator async flow."""
        task_id = str(event.get("id") or f"inventory-{uuid.uuid4().hex[:8]}")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._dispatch_event(task_id, event, {}))
        return self._error(
            "Direct handle_event unavailable in running event loop",
            "Use 'await inventory_agent.run(task_id, event, shared_context)' inside async contexts",
        )


inventory_agent = InventoryAgent()
AGENT_REGISTRY["inventory_agent"] = inventory_agent
AGENT_REGISTRY["inventory"] = inventory_agent.handle_event
logger.info("[InventoryAgent] Registered in AGENT_REGISTRY")


def handle_event(event: dict[str, Any]) -> dict[str, Any]:
    """Handle an inventory event through the module-level direct entry point."""
    return inventory_agent.handle_event(event)
