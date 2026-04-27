"""Scheduled event service for recurring MSME platform tasks."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.watcher import EventShape

logger = logging.getLogger(__name__)


async def _noop_callback(_: EventShape) -> None:
    """Provide a safe default callback until startup injection occurs."""
    return None


class SchedulerService:
    """Emit orchestrator events on recurring APScheduler jobs."""

    def __init__(self, callback: Optional[Callable[[EventShape], Awaitable[None]]]) -> None:
        self._scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        self._callback = callback or _noop_callback
        self._register_default_jobs()

    async def start(self) -> None:
        """Start the scheduler service."""
        self._scheduler.start()
        logger.info("[Scheduler] Started with timezone Asia/Kolkata")

    def stop(self) -> None:
        """Stop the scheduler service without waiting for running jobs."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def _emit(self, event_type: str, module: str, payload: dict[str, str]) -> None:
        event_shape: EventShape = {
            "type": event_type,
            "module": module,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._callback(event_shape)

    def _register_default_jobs(self) -> None:
        self._scheduler.add_job(
            self._emit,
            "cron",
            id="daily_stock_check",
            replace_existing=True,
            hour=6,
            minute=0,
            args=["scheduled_check", "inventory", {"task": "stock_check"}],
        )
        self._scheduler.add_job(
            self._emit,
            "cron",
            id="daily_ar_aging",
            replace_existing=True,
            hour=7,
            minute=0,
            args=["scheduled_check", "accounting", {"task": "ar_aging"}],
        )
        self._scheduler.add_job(
            self._emit,
            "cron",
            id="daily_customer_segmentation",
            replace_existing=True,
            hour=8,
            minute=0,
            args=["scheduled_check", "crm", {"task": "customer_segmentation"}],
        )
        self._scheduler.add_job(
            self._emit,
            "cron",
            id="month_end_payroll",
            replace_existing=True,
            day=28,
            hour=9,
            minute=0,
            args=["scheduled_check", "hr", {"task": "payroll_run"}],
        )
        self._scheduler.add_job(
            self._emit,
            "cron",
            id="month_end_gstr",
            replace_existing=True,
            day=20,
            hour=10,
            minute=0,
            args=["scheduled_check", "accounting", {"task": "gstr_prep"}],
        )
        self._scheduler.add_job(
            self._emit,
            "interval",
            id="hitl_timeout_check",
            replace_existing=True,
            minutes=30,
            args=["scheduled_check", "orchestrator", {"task": "hitl_timeout_sweep"}],
        )


scheduler_service = SchedulerService(callback=None)
