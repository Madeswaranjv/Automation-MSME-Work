"""Billing agent implementation for invoice and payment workflows."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta

from agents.hitl import HITLActionType, RiskFlag, hitl_gate
from agents.memory import memory_store
from agents.orchestrator import AGENT_REGISTRY
from agents.tools import TOOL_MAP, generate_irn, generate_pdf, send_whatsapp
from core.db import SessionLocal
from core.ws_manager import MessageType, build_ws_message, ws_manager
from modules.billing.gst_calculator import GSTBreakdown, LineItem, compute_gst, validate_hsn
from modules.billing.pdf_generator import generate_invoice_pdf

logger = logging.getLogger(__name__)
_ = (uuid, generate_pdf, generate_irn, ws_manager, MessageType, build_ws_message, GSTBreakdown)


class BillingAgent:
    """Handle GST invoice generation, sending, payment checks, and GSTR-1 prep."""

    def __init__(self) -> None:
        """Initialise the billing agent."""
        self.name = "billing_agent"
        logger.info("[BillingAgent] Initialised")

    async def run(self, task_id: str, event: dict, shared_context: dict) -> dict:
        """Route the event payload to the matching billing task handler."""
        _ = shared_context
        payload = event.get("payload", {})
        task = payload.get("task", "generate_invoice")

        memory_store.stm_append_step(
            task_id,
            "thought",
            f"BillingAgent received task='{task}'. Selecting handler.",
        )

        handlers = {
            "generate_invoice": self._handle_generate_invoice,
            "send_invoice": self._handle_send_invoice,
            "check_payment": self._handle_check_payment,
            "overdue_sweep": self._handle_overdue_sweep,
            "gstr1_data": self._handle_gstr1_data,
        }

        handler = handlers.get(task)
        if not handler:
            return {
                "success": False,
                "summary": f"Unknown task: {task}",
                "error": f"BillingAgent has no handler for task '{task}'",
            }

        try:
            return await handler(task_id, payload, shared_context)
        except Exception as exc:
            logger.error(f"[BillingAgent] Handler '{task}' failed: {exc}")
            return {
                "success": False,
                "summary": "Billing task failed",
                "error": str(exc),
            }

    async def _handle_generate_invoice(
        self,
        task_id: str,
        payload: dict,
        shared_context: dict,
    ) -> dict:
        """Generate a GST invoice PDF and persist it as a draft invoice."""
        _ = shared_context
        memory_store.stm_append_step(task_id, "thought", "Validating invoice payload fields.")

        seller = payload.get("seller", {})
        buyer = payload.get("buyer", {})
        raw_items = payload.get("line_items", [])

        if not seller.get("name") or not seller.get("gstin"):
            return {
                "success": False,
                "summary": "Missing seller info",
                "error": "seller.name and seller.gstin are required",
            }
        if not raw_items:
            return {
                "success": False,
                "summary": "No line items",
                "error": "line_items list is empty",
            }

        invalid_hsn = [
            item["hsn_code"]
            for item in raw_items
            if not validate_hsn(str(item.get("hsn_code", "")))
        ]
        if invalid_hsn:
            memory_store.stm_append_step(
                task_id,
                "observation",
                f"Invalid HSN codes found: {invalid_hsn}",
            )
            return {
                "success": False,
                "summary": "Invalid HSN codes",
                "error": f"HSN codes failed validation: {invalid_hsn}",
            }

        memory_store.stm_append_step(task_id, "action", "Computing GST breakdown.")
        line_items = [
            LineItem(
                description=str(item["description"]),
                hsn_code=str(item["hsn_code"]),
                quantity=float(item["quantity"]),
                unit_price=float(item["unit_price"]),
                gst_rate=float(item.get("gst_rate", 18.0)),
            )
            for item in raw_items
        ]
        gst = compute_gst(
            line_items,
            str(seller.get("state_code", "33")),
            str(buyer.get("state_code", "33")),
        )

        memory_store.stm_append_step(
            task_id,
            "observation",
            f"GST computed: subtotal={gst.subtotal} total={gst.total} type={gst.supply_type}",
        )

        invoice_number = payload.get("invoice_number") or (
            f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{task_id[:6].upper()}"
        )
        memory_store.stm_append_step(task_id, "action", f"Generating PDF for {invoice_number}")

        pdf_path = generate_invoice_pdf(
            invoice_number=invoice_number,
            invoice_date=datetime.utcnow().strftime("%d/%m/%Y"),
            seller=seller,
            buyer=buyer,
            line_items=raw_items,
            gst_breakdown=gst,
            due_date=payload.get("due_date"),
        )

        db = SessionLocal()
        try:
            from core.db import Invoice

            invoice = Invoice(
                invoice_number=invoice_number,
                customer_name=buyer.get("name", ""),
                customer_phone=buyer.get("phone"),
                customer_gstin=buyer.get("gstin"),
                line_items=json.dumps(raw_items),
                subtotal=gst.subtotal,
                cgst=gst.cgst_amount,
                sgst=gst.sgst_amount,
                igst=gst.igst_amount,
                total=gst.total,
                status="draft",
                created_at=datetime.utcnow(),
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            invoice_db_id = invoice.id
        finally:
            db.close()

        memory_store.stm_set_result(task_id, "invoice_number", invoice_number)
        memory_store.stm_set_result(task_id, "pdf_path", pdf_path)
        memory_store.stm_set_result(task_id, "gst_total", gst.total)
        memory_store.stm_append_step(
            task_id,
            "observation",
            f"Invoice PDF generated at {pdf_path}",
        )

        return {
            "success": True,
            "summary": f"Invoice {invoice_number} generated. Total: Rs. {gst.total}",
            "invoice_number": invoice_number,
            "pdf_path": pdf_path,
            "total": gst.total,
            "supply_type": gst.supply_type,
            "invoice_db_id": invoice_db_id,
        }

    async def _handle_send_invoice(
        self,
        task_id: str,
        payload: dict,
        shared_context: dict,
    ) -> dict:
        """Raise HITL approval and send an invoice PDF over WhatsApp."""
        _ = shared_context
        invoice_number = payload.get("invoice_number")
        customer_phone = payload.get("customer_phone")
        pdf_path = payload.get("pdf_path")

        if not all([invoice_number, customer_phone, pdf_path]):
            return {
                "success": False,
                "summary": "Missing send payload",
                "error": "invoice_number, customer_phone and pdf_path required",
            }

        memory_store.stm_append_step(
            task_id,
            "thought",
            f"Preparing to send {invoice_number} to {customer_phone}. HITL gate required.",
        )

        hitl_id = await hitl_gate.create_request(
            task_id=task_id,
            agent_name=self.name,
            action_type=HITLActionType.INVOICE_SEND,
            action_preview={
                "invoice_number": invoice_number,
                "customer_phone": customer_phone,
                "pdf_path": pdf_path,
                "message": f"Send invoice {invoice_number} to {customer_phone} via WhatsApp",
            },
            risk_flag=RiskFlag.LOW,
        )

        memory_store.stm_append_step(
            task_id,
            "observation",
            f"HITL gate raised. hitl_id={hitl_id}. Awaiting owner approval.",
        )

        decision = await hitl_gate.wait_for_decision(hitl_id)
        if not decision["approved"]:
            memory_store.stm_append_step(
                task_id,
                "observation",
                f"Owner rejected send. Reason: {decision.get('reason')}",
            )
            return {
                "success": False,
                "summary": f"Invoice send rejected by owner: {decision.get('reason')}",
                "hitl_resolved": True,
            }

        memory_store.stm_append_step(
            task_id,
            "action",
            f"Owner approved. Sending {invoice_number} via WhatsApp.",
        )

        whatsapp_tool = TOOL_MAP.get("send_whatsapp", send_whatsapp)
        result = whatsapp_tool.invoke(
            {
                "phone_number": customer_phone,
                "message": f"Dear Customer, please find your invoice {invoice_number} attached.",
                "document_path": pdf_path,
            }
        )

        db = SessionLocal()
        try:
            from core.db import Invoice

            invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
            if invoice:
                invoice.status = "sent"
                db.commit()
        finally:
            db.close()

        memory_store.stm_append_step(task_id, "observation", f"WhatsApp send result: {result}")
        return {
            "success": result.get("success", False),
            "summary": f"Invoice {invoice_number} sent to {customer_phone}",
            "whatsapp_result": result,
            "hitl_resolved": True,
        }

    async def _handle_check_payment(
        self,
        task_id: str,
        payload: dict,
        shared_context: dict,
    ) -> dict:
        """Check sent invoices and mark overdue records after three days."""
        _ = shared_context
        memory_store.stm_append_step(
            task_id,
            "thought",
            "Checking payment status of sent invoices.",
        )

        overdue_threshold = timedelta(days=3)
        db = SessionLocal()
        try:
            from core.db import Invoice

            query = db.query(Invoice).filter(Invoice.status == "sent")
            if payload.get("invoice_number"):
                query = query.filter(Invoice.invoice_number == payload["invoice_number"])
            invoices = query.all()

            overdue_count = 0
            for invoice in invoices:
                if datetime.utcnow() - invoice.created_at >= overdue_threshold and invoice.status == "sent":
                    invoice.status = "overdue"
                    overdue_count += 1
            db.commit()

            memory_store.stm_append_step(
                task_id,
                "observation",
                f"Found {len(invoices)} sent invoices. Marked {overdue_count} as overdue.",
            )
            return {
                "success": True,
                "summary": f"Payment check complete. {overdue_count} invoices now overdue.",
                "checked_count": len(invoices),
                "overdue_count": overdue_count,
            }
        finally:
            db.close()

    async def _handle_overdue_sweep(
        self,
        task_id: str,
        payload: dict,
        shared_context: dict,
    ) -> dict:
        """Collect overdue invoices and store them for CRM escalation."""
        _ = (payload, shared_context)
        memory_store.stm_append_step(
            task_id,
            "thought",
            "Sweeping overdue invoices for escalation list.",
        )

        db = SessionLocal()
        try:
            from core.db import Invoice

            overdue = db.query(Invoice).filter(Invoice.status == "overdue").all()
            overdue_list = [
                {
                    "invoice_number": invoice.invoice_number,
                    "customer_name": invoice.customer_name,
                    "customer_phone": invoice.customer_phone,
                    "total": invoice.total,
                    "days_overdue": (datetime.utcnow() - invoice.created_at).days,
                }
                for invoice in overdue
            ]

            memory_store.stm_append_step(
                task_id,
                "observation",
                f"{len(overdue_list)} overdue invoices ready for CRM escalation.",
            )
            if overdue_list:
                memory_store.ltm_write(
                    agent_name=self.name,
                    task_id=task_id,
                    summary=f"Overdue invoices: {json.dumps(overdue_list)}",
                    metadata={"type": "overdue_list", "count": len(overdue_list)},
                )

            return {
                "success": True,
                "summary": f"{len(overdue_list)} overdue invoices logged for CRM escalation.",
                "overdue_invoices": overdue_list,
            }
        finally:
            db.close()

    async def _handle_gstr1_data(
        self,
        task_id: str,
        payload: dict,
        shared_context: dict,
    ) -> dict:
        """Build monthly GSTR-1-ready invoice records from sent and paid invoices."""
        _ = shared_context
        month = payload.get("month", datetime.utcnow().strftime("%Y-%m"))
        memory_store.stm_append_step(
            task_id,
            "thought",
            f"Building GSTR-1 data for month={month}",
        )

        db = SessionLocal()
        try:
            from core.db import Invoice
            from sqlalchemy import func

            invoices = db.query(Invoice).filter(
                Invoice.status.in_(["sent", "paid"]),
                func.strftime("%Y-%m", Invoice.created_at) == month,
            ).all()

            gstr1_records = [
                {
                    "invoice_number": invoice.invoice_number,
                    "customer_gstin": invoice.customer_gstin or "URP",
                    "customer_name": invoice.customer_name,
                    "invoice_date": invoice.created_at.strftime("%d/%m/%Y"),
                    "subtotal": invoice.subtotal,
                    "cgst": invoice.cgst,
                    "sgst": invoice.sgst,
                    "igst": invoice.igst,
                    "total": invoice.total,
                }
                for invoice in invoices
            ]

            memory_store.stm_append_step(
                task_id,
                "observation",
                f"GSTR-1 data built: {len(gstr1_records)} invoices for {month}",
            )
            return {
                "success": True,
                "summary": f"GSTR-1 data ready: {len(gstr1_records)} invoices for {month}",
                "month": month,
                "record_count": len(gstr1_records),
                "gstr1_records": gstr1_records,
            }
        finally:
            db.close()


billing_agent = BillingAgent()
AGENT_REGISTRY["billing_agent"] = billing_agent
logger.info("[BillingAgent] Registered in AGENT_REGISTRY")
