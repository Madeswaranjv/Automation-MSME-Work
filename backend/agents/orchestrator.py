"""LangGraph orchestration entry point for all platform events."""

from __future__ import annotations

import logging
import operator
import json
import uuid
from datetime import datetime
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from core.watcher import EventShape
from core.ws_manager import MessageType, build_ws_message, ws_manager

from agents.hitl import HITLActionType, RiskFlag, hitl_gate
from agents.memory import memory_store

logger = logging.getLogger(__name__)
_ = (HITLActionType, RiskFlag, json)


class OrchestratorState(TypedDict):
    """Define the shared state schema for the orchestration graph."""

    task_id: str
    event: dict
    module: str
    agent_name: str
    agent_result: dict
    hitl_required: bool
    hitl_id: str
    hitl_approved: bool
    error: str | None
    steps: Annotated[list, operator.add]


MODULE_TO_AGENT = {
    "billing": "billing_agent",
    "inventory": "inventory_agent",
    "accounting": "accounting_agent",
    "hr": "hr_agent",
    "crm": "crm_agent",
    "credit": "credit_agent",
    "orchestrator": "orchestrator",
}

AGENT_REGISTRY: dict[str, Any] = {}


async def route_node(state: OrchestratorState) -> OrchestratorState:
    """Inspect the event, select an agent, initialise STM, and notify the dashboard."""
    event = state["event"]
    module = event.get("module", "orchestrator")
    agent_name = MODULE_TO_AGENT.get(module, "orchestrator")
    task_id = str(uuid.uuid4())
    memory_store.stm_init(task_id, agent_name, event.get("payload", {}))
    memory_store.stm_append_step(
        task_id,
        "thought",
        f"Received event type={event.get('type')} module={module}. Routing to {agent_name}.",
    )
    await ws_manager.broadcast(
        build_ws_message(
            MessageType.AGENT_UPDATE,
            agent=agent_name,
            data={
                "task_id": task_id,
                "status": "started",
                "module": module,
                "trigger": event.get("type"),
                "timestamp": datetime.utcnow().isoformat(),
            },
        ),
        room="dashboard",
    )
    logger.info(f"[Orchestrator] task={task_id} routed to {agent_name}")
    return {
        **state,
        "task_id": task_id,
        "module": module,
        "agent_name": agent_name,
        "steps": [
            {
                "role": "thought",
                "content": f"Routing to {agent_name}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
    }


async def dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """Dispatch the event to a registered agent or run built-in orchestrator tasks."""
    agent_name = state["agent_name"]
    task_id = state["task_id"]
    event_payload = state["event"].get("payload", {})
    agent = AGENT_REGISTRY.get(agent_name)
    if agent_name == "orchestrator" and event_payload.get("task") == "hitl_timeout_sweep":
        memory_store.stm_append_step(task_id, "action", "Calling hitl_gate.sweep_timeouts()")
        timed_out_count = await hitl_gate.sweep_timeouts()
        result = {
            "success": True,
            "summary": f"Swept {timed_out_count} expired HITL requests",
            "timed_out_count": timed_out_count,
            "hitl_required": False,
            "hitl_id": "",
        }
        memory_store.stm_append_step(
            task_id,
            "observation",
            f"Timeout sweep completed. timed_out_count={timed_out_count}",
        )
    elif not agent:
        logger.warning(f"[Orchestrator] Agent '{agent_name}' not registered yet.")
        result = {
            "success": False,
            "error": f"Agent {agent_name} not registered",
            "note": "Teammate has not implemented this agent yet",
        }
    else:
        try:
            memory_store.stm_append_step(task_id, "action", f"Calling {agent_name}.run()")
            result = await agent.run(
                task_id=task_id,
                event=state["event"],
                shared_context=memory_store.get_shared_context(),
            )
            memory_store.stm_append_step(
                task_id,
                "observation",
                f"{agent_name} completed. success={result.get('success')}",
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] Agent {agent_name} raised: {exc}")
            result = {"success": False, "error": str(exc)}
    hitl_required = result.get("hitl_required", False)
    hitl_id = result.get("hitl_id", "")
    await ws_manager.broadcast(
        build_ws_message(
            MessageType.AGENT_UPDATE,
            agent=agent_name,
            data={
                "task_id": task_id,
                "status": "hitl_pending"
                if hitl_required
                else ("completed" if result.get("success") else "error"),
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.utcnow().isoformat(),
            },
        ),
        room="dashboard",
    )
    stm = memory_store.stm_get(task_id)
    memory_store.write_episode(
        task_id=task_id,
        agent_name=agent_name,
        trigger_type=state["event"].get("type", "unknown"),
        trigger_payload=state["event"].get("payload", {}),
        steps=stm["react_scratchpad"] if stm else [],
        outcome="hitl_pending" if hitl_required else ("success" if result.get("success") else "failed"),
        error_message=result.get("error"),
        started_at=datetime.fromisoformat(stm["started_at"]) if stm else None,
    )
    memory_store.stm_clear(task_id)
    return {
        **state,
        "agent_result": result,
        "hitl_required": hitl_required,
        "hitl_id": hitl_id,
        "steps": [
            {
                "role": "observation",
                "content": f"Agent result: success={result.get('success')}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
    }


def build_graph() -> Any:
    """Build and compile the orchestrator StateGraph."""
    graph = StateGraph(OrchestratorState)
    graph.add_node("route", route_node)
    graph.add_node("dispatch", dispatch_node)
    graph.set_entry_point("route")
    graph.add_edge("route", "dispatch")
    graph.add_edge("dispatch", END)
    return graph.compile()


orchestrator_graph = build_graph()


async def handle_event(event: EventShape) -> dict[str, Any]:
    """Run the full orchestration graph for a single watcher or scheduler event."""
    initial_state: OrchestratorState = {
        "task_id": "",
        "event": dict(event),
        "module": "",
        "agent_name": "",
        "agent_result": {},
        "hitl_required": False,
        "hitl_id": "",
        "hitl_approved": False,
        "error": None,
        "steps": [],
    }
    try:
        result = await orchestrator_graph.ainvoke(initial_state)
        return dict(result)
    except Exception as exc:
        logger.error(f"[Orchestrator] Graph execution failed: {exc}")
        return {**initial_state, "error": str(exc)}
