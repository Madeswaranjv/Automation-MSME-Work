"""Focused tests for CRM agent billing sync, segmentation, and HITL flow."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
import gc
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import close_all_sessions


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class CRMAgentTestCase(unittest.TestCase):
    """Validate the CRM agent end to end against a temporary SQLite database."""

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "crm_test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.db_path.as_posix()}"
        self.crm_module = self._reload_module("agents.crm_agent")
        self.hitl_module = importlib.import_module("agents.hitl")
        self.agent = self.crm_module.crm_agent

    def tearDown(self) -> None:
        try:
            core_db = importlib.import_module("core.db")
            close_all_sessions()
            core_db.get_engine().dispose()
            core_db.get_engine.cache_clear()
        except Exception:
            pass
        self.agent = None
        self.crm_module = None
        self.hitl_module = None
        gc.collect()
        self._temp_dir.cleanup()

    def _reload_module(self, module_name: str):
        stale_modules = [
            loaded_name
            for loaded_name in list(sys.modules)
            if loaded_name in {"agents", "core", module_name}
            or loaded_name.startswith("agents.")
            or loaded_name.startswith("core.")
        ]
        for loaded_name in stale_modules:
            sys.modules.pop(loaded_name, None)
        importlib.invalidate_caches()
        return importlib.import_module(module_name)

    def _billing_event(
        self,
        *,
        event_id: str,
        invoice_number: str,
        total: float,
        days_ago: int = 0,
    ) -> dict:
        purchase_date = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
        return {
            "id": event_id,
            "type": "ACTION",
            "module": "billing",
            "source": "billing_agent",
            "payload": {
                "action": "invoice_created",
                "invoice_number": invoice_number,
                "customer": {
                    "name": "Acme Stores",
                    "phone": "9876543210",
                    "email": "owner@acme.test",
                    "gstin": "29ABCDE1234F1Z5",
                },
                "items": [
                    {"sku": "SKU-1", "name": "Product A", "quantity": 2, "price": 125.0},
                    {"sku": "SKU-2", "name": "Product B", "quantity": 1, "price": 0.0},
                ],
                "total": total,
                "purchase_date": purchase_date,
            },
            "timestamp": purchase_date,
        }

    def test_invoice_event_creates_customer_and_history(self) -> None:
        result = self.agent.handle_event(
            self._billing_event(event_id="evt-1", invoice_number="INV-001", total=250.0)
        )

        self.assertTrue(result["success"])
        customer = result["data"]["customer"]
        self.assertEqual(customer["name"], "Acme Stores")
        self.assertEqual(customer["purchase_count"], 1)
        self.assertEqual(customer["total_spent"], 250.0)
        self.assertEqual(result["data"]["purchase_history"]["invoice_reference"], "INV-001")

        list_result = self.agent.list_customers()
        self.assertEqual(list_result["data"]["count"], 1)

    def test_multiple_invoices_update_customer_stats(self) -> None:
        self.agent.handle_event(self._billing_event(event_id="evt-1", invoice_number="INV-001", total=250.0))
        self.agent.handle_event(self._billing_event(event_id="evt-2", invoice_number="INV-002", total=400.0))

        top_customers = self.agent.top_customers()
        customer = top_customers["data"]["customers"][0]
        self.assertEqual(customer["purchase_count"], 2)
        self.assertEqual(customer["total_spent"], 650.0)

        history = self.agent.get_customer_history(customer["id"])
        self.assertEqual(history["data"]["count"], 2)

    def test_segmentation_and_inactive_detection(self) -> None:
        active = self.agent.create_customer(name="Active Buyer", phone="9000000001")
        warm = self.agent.create_customer(name="Warm Buyer", phone="9000000002")
        inactive = self.agent.create_customer(name="Inactive Buyer", phone="9000000003")

        self.agent.update_customer(
            active["data"]["customer"]["id"],
            total_spent=100.0,
            purchase_count=1,
            last_purchase_date=(datetime.utcnow() - timedelta(days=2)).isoformat(),
        )
        self.agent.update_customer(
            warm["data"]["customer"]["id"],
            total_spent=200.0,
            purchase_count=2,
            last_purchase_date=(datetime.utcnow() - timedelta(days=10)).isoformat(),
        )
        self.agent.update_customer(
            inactive["data"]["customer"]["id"],
            total_spent=300.0,
            purchase_count=3,
            last_purchase_date=(datetime.utcnow() - timedelta(days=45)).isoformat(),
        )

        segmentation = self.agent.segment_customers()
        self.assertEqual(segmentation["data"]["segments"]["Active"], 1)
        self.assertEqual(segmentation["data"]["segments"]["Warm"], 1)
        self.assertEqual(segmentation["data"]["segments"]["Inactive"], 1)

        inactive_customers = self.agent.get_inactive_customers(days=30)
        self.assertEqual(inactive_customers["data"]["count"], 1)
        self.assertEqual(inactive_customers["data"]["customers"][0]["name"], "Inactive Buyer")

    def test_campaign_suggestion_raises_hitl_request(self) -> None:
        customer = self.agent.create_customer(name="Dormant Buyer", phone="9000000099")
        self.agent.update_customer(
            customer["data"]["customer"]["id"],
            total_spent=500.0,
            purchase_count=4,
            last_purchase_date=(datetime.utcnow() - timedelta(days=60)).isoformat(),
        )

        result = self.agent.handle_event(
            {
                "id": "crm-task-1",
                "type": "ACTION",
                "module": "crm",
                "payload": {
                    "action": "suggest_campaign",
                    "days": 30,
                    "discount_percentage": 10,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["hitl_required"])
        self.assertTrue(result["hitl_id"])
        self.assertEqual(result["data"]["campaign"]["recipient_count"], 1)

        pending = self.hitl_module.hitl_gate.get_pending_list()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["action_type"], "whatsapp_broadcast")


if __name__ == "__main__":
    unittest.main()
