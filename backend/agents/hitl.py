"""Human-in-the-loop approval gate services."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from core.db import HITLRequest, SessionLocal
from core.ws_manager import MessageType, build_ws_message, ws_manager

from agents.memory import memory_store

logger = logging.getLogger(__name__)


class HITLActionType(str, Enum):
    """Enumerate supported approval-gated business actions."""

    NEFT_TRANSFER = "neft_transfer"
    GSTR_FILING = "gstr_filing"
    WHATSAPP_BROADCAST = "whatsapp_broadcast"
    LOAN_SUBMISSION = "loan_submission"
    INVOICE_SEND = "invoice_send"
    PO_GENERATE = "po_generate"
    CREDIT_NOTE = "credit_note"


class RiskFlag(str, Enum):
    """Enumerate supported risk levels for HITL requests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


MANDATORY_HITL_ACTIONS = {
    HITLActionType.NEFT_TRANSFER,
    HITLActionType.GSTR_FILING,
    HITLActionType.LOAN_SUBMISSION,
}


class HITLGateService:
    """Manage lifecycle, persistence, and signalling for HITL approvals."""

    def __init__(self) -> None:
        """Initialise in-memory wait handles and decision cache."""
        self._pending: dict[str, asyncio.Event] = {}
        self._decisions: dict[str, dict[str, Any]] = {}
        logger.info("[HITL] HITLGateService initialised")

    async def create_request(
        self,
        task_id: str,
        agent_name: str,
        action_type: HITLActionType,
        action_preview: dict[str, Any],
        risk_flag: RiskFlag = RiskFlag.MEDIUM,
        timeout_hours: int = 24,
    ) -> str:
        """Create, persist, and broadcast a new HITL approval request."""
        db = SessionLocal()
        try:
            hitl_id = str(uuid.uuid4())
            timeout_at = datetime.utcnow() + timedelta(hours=timeout_hours)
            req = HITLRequest(
                task_id=task_id,
                agent_name=agent_name,
                action_type=action_type.value,
                action_preview=json.dumps(action_preview),
                risk_flag=risk_flag.value,
                status="pending",
                created_at=datetime.utcnow(),
                timeout_at=timeout_at,
            )
            db.add(req)
            db.commit()
            db.refresh(req)
            hitl_id = str(req.id)
            self._pending[hitl_id] = asyncio.Event()
            memory_store.add_active_hitl(task_id)
            ws_payload = build_ws_message(
                msg_type=MessageType.HITL_REQUEST,
                agent=agent_name,
                data={
                    "hitl_id": hitl_id,
                    "task_id": task_id,
                    "action_type": action_type.value,
                    "action_preview": action_preview,
                    "risk_flag": risk_flag.value,
                    "created_at": datetime.utcnow().isoformat(),
                    "timeout_at": timeout_at.isoformat(),
                },
            )
            await ws_manager.broadcast(ws_payload, room="hitl_inbox")
            await ws_manager.broadcast(ws_payload, room="dashboard")
            logger.info(f"[HITL] Request created: id={hitl_id} action={action_type.value} task={task_id}")
            return hitl_id
        except Exception as exc:
            logger.error(f"[HITL] Failed to create request: {exc}")
            db.rollback()
            raise
        finally:
            db.close()

    async def wait_for_decision(self, hitl_id: str, timeout_seconds: int = 86400) -> dict[str, Any]:
        """Suspend until a HITL request is approved, rejected, or timed out."""
        event = self._pending.get(hitl_id)
        if not event:
            return {"approved": False, "reason": "HITL request not found"}
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
            return self._decisions.get(hitl_id, {"approved": False, "reason": "No decision recorded"})
        except asyncio.TimeoutError:
            logger.warning(f"[HITL] Timeout for hitl_id={hitl_id}")
            await self._mark_timeout(hitl_id)
            return {"approved": False, "reason": "timeout"}

    async def resolve(self, hitl_id: str, approved: bool, reason: str | None = None) -> bool:
        """Persist and signal an owner decision for a pending HITL request."""
        db = SessionLocal()
        try:
            req = db.query(HITLRequest).filter(HITLRequest.id == int(hitl_id)).first()
            if not req or req.status != "pending":
                return False
            req.status = "approved" if approved else "rejected"
            req.owner_decision = "approved" if approved else "rejected"
            req.rejection_reason = reason
            req.decided_at = datetime.utcnow()
            db.commit()
            self._decisions[hitl_id] = {"approved": approved, "reason": reason}
            if hitl_id in self._pending:
                self._pending[hitl_id].set()
            memory_store.remove_active_hitl(req.task_id)
            ws_payload = build_ws_message(
                msg_type=MessageType.HITL_RESOLVED,
                data={
                    "hitl_id": hitl_id,
                    "approved": approved,
                    "reason": reason,
                    "decided_at": datetime.utcnow().isoformat(),
                },
            )
            await ws_manager.broadcast(ws_payload, room="hitl_inbox")
            await ws_manager.broadcast(ws_payload, room="dashboard")
            logger.info(f"[HITL] Resolved: id={hitl_id} approved={approved}")
            return True
        except Exception as exc:
            logger.error(f"[HITL] Failed to resolve: {exc}")
            db.rollback()
            return False
        finally:
            db.close()

    async def sweep_timeouts(self) -> int:
        """Mark all expired pending HITL requests as timed out."""
        db = SessionLocal()
        count = 0
        try:
            expired = db.query(HITLRequest).filter(
                HITLRequest.status == "pending",
                HITLRequest.timeout_at <= datetime.utcnow(),
            ).all()
            for req in expired:
                req.status = "timeout"
                req.decided_at = datetime.utcnow()
                db.commit()
                hitl_id = str(req.id)
                self._decisions[hitl_id] = {"approved": False, "reason": "timeout"}
                if hitl_id in self._pending:
                    self._pending[hitl_id].set()
                memory_store.remove_active_hitl(req.task_id)
                count += 1
            if count:
                logger.info(f"[HITL] Timeout sweep: {count} requests cancelled")
        except Exception as exc:
            logger.error(f"[HITL] Sweep failed: {exc}")
            db.rollback()
        finally:
            db.close()
        return count

    async def _mark_timeout(self, hitl_id: str) -> None:
        """Mark a single HITL request as timed out in persistent storage."""
        db = SessionLocal()
        try:
            req = db.query(HITLRequest).filter(HITLRequest.id == int(hitl_id)).first()
            if req and req.status == "pending":
                req.status = "timeout"
                req.decided_at = datetime.utcnow()
                db.commit()
                self._decisions[hitl_id] = {"approved": False, "reason": "timeout"}
                memory_store.remove_active_hitl(req.task_id)
        finally:
            db.close()

    def get_pending_list(self) -> list[dict[str, Any]]:
        """Return all currently pending HITL requests."""
        db = SessionLocal()
        try:
            reqs = db.query(HITLRequest).filter(HITLRequest.status == "pending").all()
            return [
                {
                    "hitl_id": str(req.id),
                    "task_id": req.task_id,
                    "agent_name": req.agent_name,
                    "action_type": req.action_type,
                    "action_preview": json.loads(req.action_preview),
                    "risk_flag": req.risk_flag,
                    "created_at": req.created_at.isoformat(),
                    "timeout_at": req.timeout_at.isoformat() if req.timeout_at else None,
                }
                for req in reqs
            ]
        finally:
            db.close()


hitl_gate = HITLGateService()
