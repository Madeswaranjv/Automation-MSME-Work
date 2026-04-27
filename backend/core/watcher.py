"""Filesystem watcher service for inbound business data files."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Optional, TypedDict

import watchdog.events
import watchdog.observers
from watchdog.events import FileSystemEvent

logger = logging.getLogger(__name__)


class EventShape(TypedDict):
    """Define the normalized event contract for platform services."""

    type: str
    module: str
    payload: dict[str, str]
    timestamp: str


async def _noop_callback(_: EventShape) -> None:
    """Provide a safe default callback until startup injection occurs."""
    return None


class TallyFileHandler(watchdog.events.FileSystemEventHandler):
    """Transform filesystem notifications into orchestrator events."""

    def __init__(
        self,
        callback: Optional[Callable[[EventShape], Awaitable[None]]],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.callback = callback or _noop_callback
        self.loop = loop
        super().__init__()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle new files created in the watched directory."""
        self._handle_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle existing files modified in the watched directory."""
        self._handle_event(event)

    def _handle_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        extension = Path(event.src_path).suffix.lower()
        if extension not in {".xml", ".csv", ".xlsx"}:
            return

        module = "tally" if extension == ".xml" else "excel"
        event_shape: EventShape = {
            "type": "file_event",
            "module": module,
            "payload": {
                "file_path": event.src_path,
                "file_name": Path(event.src_path).name,
                "extension": extension,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        future = asyncio.run_coroutine_threadsafe(self.callback(event_shape), self.loop)
        future.add_done_callback(self._log_future_exception)
        logger.info(f"[Watcher] New file detected: {event_shape}")

    def _log_future_exception(self, future: asyncio.Future[None]) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("[Watcher] Callback execution failed.")


class FileWatcherService:
    """Manage the watchdog observer lifecycle for inbound files."""

    def __init__(
        self,
        watch_dir: str,
        callback: Optional[Callable[[EventShape], Awaitable[None]]],
    ) -> None:
        self.watch_dir = watch_dir
        self.callback = callback
        self._observer = watchdog.observers.Observer()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start watching the configured directory on the given loop."""
        self._loop = loop
        os.makedirs(self.watch_dir, exist_ok=True)
        handler = TallyFileHandler(self.callback, loop)
        self._observer.schedule(handler, self.watch_dir, recursive=False)
        self._observer.start()
        logger.info(f"[Watcher] Watching: {self.watch_dir}")

    def stop(self) -> None:
        """Stop the observer thread cleanly."""
        self._observer.stop()
        if self._observer.is_alive():
            self._observer.join()
        logger.info("[Watcher] Stopped.")


WATCH_DIR = os.getenv("TALLY_WATCH_DIR", "./watched_files")
watcher_service = FileWatcherService(WATCH_DIR, callback=None)
