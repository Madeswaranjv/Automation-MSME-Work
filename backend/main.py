"""FastAPI entry point for the MSME AI Platform backend."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func

load_dotenv()

from core.db import AgentLog, Customer, HITLRequest, InventoryItem, Invoice, SessionLocal, init_db
from core.scheduler import scheduler_service
from core.watcher import EventShape, watcher_service
from core.ws_manager import MessageType, build_ws_message, ws_manager

import agents.billing_agent  # noqa: F401
import agents.accounting_agent  # noqa: F401
import agents.crm_agent  # noqa: F401
import agents.inventory_agent  # noqa: F401
from agents.hitl import hitl_gate
from agents.orchestrator import handle_event

logger = logging.getLogger(__name__)
VALID_WS_ROOMS = {"dashboard", "hitl_inbox"}
_ = (MessageType, build_ws_message, json, os)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the backend services alongside the FastAPI app."""
    logger.info("[Main] Starting MSME AI Platform backend...")
    _ = app
    init_db()
    loop = asyncio.get_event_loop()
    watcher_service.callback = handle_event
    scheduler_service._callback = handle_event
    await watcher_service.start(loop)
    await scheduler_service.start()
    logger.info("[Main] All services started. Backend ready.")
    yield
    watcher_service.stop()
    scheduler_service.stop()
    logger.info("[Main] Backend shutdown complete.")


app = FastAPI(title="MSME AI Platform", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a simple health response for uptime checks."""
    return {"status": "ok", "version": "2.0.0", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/hitl/pending")
async def get_pending_hitl() -> list[dict[str, Any]]:
    """Return the list of currently pending HITL approval requests."""
    return hitl_gate.get_pending_list()


@app.post("/api/hitl/{hitl_id}/resolve")
async def resolve_hitl(hitl_id: str, body: dict[str, Any]) -> dict[str, bool]:
    """Resolve a pending HITL approval request as approved or rejected."""
    approved = bool(body.get("approved"))
    reason = body.get("reason")
    success = await hitl_gate.resolve(hitl_id, approved, reason)
    if not success:
        raise HTTPException(status_code=404, detail="HITL request not found")
    return {"success": True}


@app.get("/api/agent-log")
async def get_agent_log(limit: int = 20, agent_name: str | None = None) -> list[dict[str, Any]]:
    """Return the latest agent log entries with optional agent filtering."""
    db = SessionLocal()
    try:
        query = db.query(AgentLog)
        if agent_name:
            query = query.filter(AgentLog.agent_name == agent_name)
        rows = query.order_by(AgentLog.started_at.desc()).limit(max(limit, 1)).all()
        return [
            {
                "task_id": row.task_id,
                "agent_name": row.agent_name,
                "trigger_type": row.trigger_type,
                "outcome": row.outcome,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "duration_ms": row.duration_ms,
                "error_message": row.error_message,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/api/kpi/summary")
async def get_kpi_summary() -> dict[str, Any]:
    """Return summary KPI counts and aggregates from the SQLite database."""
    db = SessionLocal()
    try:
        total_invoices = db.query(func.count(Invoice.id)).scalar() or 0
        total_revenue = (
            db.query(func.coalesce(func.sum(Invoice.total), 0.0))
            .filter(Invoice.status == "paid")
            .scalar()
            or 0.0
        )
        pending_hitl = db.query(func.count(HITLRequest.id)).filter(HITLRequest.status == "pending").scalar() or 0
        low_stock_items = (
            db.query(func.count(InventoryItem.id))
            .filter(InventoryItem.quantity <= InventoryItem.reorder_level)
            .scalar()
            or 0
        )
        active_customers = db.query(func.count(Customer.id)).scalar() or 0
        return {
            "total_invoices": int(total_invoices),
            "total_revenue": float(total_revenue),
            "pending_hitl": int(pending_hitl),
            "low_stock_items": int(low_stock_items),
            "active_customers": int(active_customers),
        }
    finally:
        db.close()


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str) -> None:
    """Handle websocket clients for dashboard and HITL inbox rooms."""
    if room not in VALID_WS_ROOMS:
        await websocket.close(code=1008)
        return
    await ws_manager.connect(websocket, room)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room)
    except Exception:
        ws_manager.disconnect(websocket, room)
        raise


@app.post("/api/trigger/manual")
async def trigger_manual(body: dict[str, Any]) -> dict[str, Any]:
    """Trigger the orchestrator manually with a synthetic EventShape payload."""
    event_shape: EventShape = {
        "type": str(body.get("type", "")),
        "module": str(body.get("module", "orchestrator")),
        "payload": body.get("payload", {}) or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    return await handle_event(event_shape)
