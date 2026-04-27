"""Memory services for orchestrated agent execution."""

from __future__ import annotations

import json
import logging
import os
import typing
import uuid
from datetime import datetime

import chromadb

from core.db import AgentLog, SessionLocal

logger = logging.getLogger(__name__)


class SharedContext(typing.TypedDict):
    """Define shared business context available to all agents."""

    current_date: str
    owner_name: str
    business_name: str
    gst_number: str
    preferred_language: str
    active_hitl_task_ids: list[str]


DEFAULT_SHARED_CONTEXT: SharedContext = {
    "current_date": "",
    "owner_name": "Owner",
    "business_name": "My Business",
    "gst_number": "",
    "preferred_language": "en",
    "active_hitl_task_ids": [],
}


class AgentMemoryStore:
    """Manage short-term, shared, episodic, and long-term agent memory."""

    def __init__(self) -> None:
        """Initialise in-memory state and the Chroma long-term store."""
        self._stm: dict[str, dict[str, typing.Any]] = {}
        self._shared_context: SharedContext = typing.cast(SharedContext, DEFAULT_SHARED_CONTEXT.copy())
        self._shared_context["active_hitl_task_ids"] = list(DEFAULT_SHARED_CONTEXT["active_hitl_task_ids"])
        self._chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_DB_PATH", "./chroma_db")
        )
        self._ltm_collection = self._chroma_client.get_or_create_collection(
            name="agent_ltm",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("[Memory] AgentMemoryStore initialised")
        _ = uuid.UUID

    def stm_init(self, task_id: str, agent_name: str, trigger_payload: dict) -> None:
        """Initialise a new short-term memory session for a task."""
        self._stm[task_id] = {
            "agent_name": agent_name,
            "trigger_payload": trigger_payload,
            "react_scratchpad": [],
            "intermediate_results": {},
            "started_at": datetime.utcnow().isoformat(),
        }

    def stm_append_step(self, task_id: str, role: str, content: str) -> None:
        """Append a ReAct scratchpad step for the active task."""
        if task_id not in self._stm:
            return
        self._stm[task_id]["react_scratchpad"].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def stm_set_result(self, task_id: str, key: str, value: typing.Any) -> None:
        """Store an intermediate result in short-term memory."""
        if task_id in self._stm:
            self._stm[task_id]["intermediate_results"][key] = value

    def stm_get(self, task_id: str) -> dict[str, typing.Any] | None:
        """Return the full short-term memory session for a task."""
        return self._stm.get(task_id)

    def stm_clear(self, task_id: str) -> None:
        """Clear short-term memory for a completed task."""
        self._stm.pop(task_id, None)

    def ltm_write(
        self,
        agent_name: str,
        task_id: str,
        summary: str,
        metadata: dict[str, typing.Any] | None = None,
    ) -> None:
        """Write a task summary into Chroma long-term memory."""
        try:
            doc_id = f"{agent_name}_{task_id}"
            meta: dict[str, typing.Any] = {
                "agent_name": agent_name,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if metadata:
                meta.update(metadata)
            self._ltm_collection.add(documents=[summary], ids=[doc_id], metadatas=[meta])
        except Exception as exc:
            logger.error(f"[Memory] LTM write failed: {exc}")

    def ltm_search(
        self,
        query: str,
        agent_name: str | None = None,
        n_results: int = 3,
    ) -> list[dict[str, typing.Any]]:
        """Run semantic search against Chroma long-term memory."""
        try:
            where = {"agent_name": agent_name} if agent_name else None
            results = self._ltm_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
            )
            documents = results.get("documents", [[]]) or [[]]
            metadatas = results.get("metadatas", [[]]) or [[]]
            distances = results.get("distances", [[]]) or [[]]
            out: list[dict[str, typing.Any]] = []
            for index, document in enumerate(documents[0]):
                out.append(
                    {
                        "document": document,
                        "metadata": metadatas[0][index] if metadatas[0] else {},
                        "distance": distances[0][index] if distances[0] else None,
                    }
                )
            return out
        except Exception as exc:
            logger.error(f"[Memory] LTM search failed: {exc}")
            return []

    def get_shared_context(self) -> SharedContext:
        """Return a copy of the shared context for downstream agents."""
        self._shared_context["current_date"] = datetime.utcnow().date().isoformat()
        return typing.cast(SharedContext, self._shared_context.copy())

    def update_shared_context(self, updates: dict[str, typing.Any]) -> None:
        """Merge partial updates into the shared context."""
        self._shared_context.update(updates)

    def add_active_hitl(self, task_id: str) -> None:
        """Track a task as pending human approval."""
        if task_id not in self._shared_context["active_hitl_task_ids"]:
            self._shared_context["active_hitl_task_ids"].append(task_id)

    def remove_active_hitl(self, task_id: str) -> None:
        """Remove a task from the pending human approval list."""
        ids = self._shared_context["active_hitl_task_ids"]
        if task_id in ids:
            ids.remove(task_id)

    def write_episode(
        self,
        task_id: str,
        agent_name: str,
        trigger_type: str,
        trigger_payload: dict,
        steps: list[typing.Any],
        outcome: str,
        error_message: str | None = None,
        started_at: datetime | None = None,
    ) -> None:
        """Persist a completed task trace into the SQLite agent log."""
        db = SessionLocal()
        try:
            episode = AgentLog(
                task_id=task_id,
                agent_name=agent_name,
                trigger_type=trigger_type,
                trigger_payload=json.dumps(trigger_payload),
                steps=json.dumps(steps),
                outcome=outcome,
                error_message=error_message,
                started_at=started_at or datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            if started_at:
                delta = datetime.utcnow() - started_at
                episode.duration_ms = int(delta.total_seconds() * 1000)
            db.add(episode)
            db.commit()
        except Exception as exc:
            logger.error(f"[Memory] Episode write failed: {exc}")
            db.rollback()
        finally:
            db.close()


memory_store = AgentMemoryStore()
