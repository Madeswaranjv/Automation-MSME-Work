# MSME AI Platform
### Agentic Edition — Privacy-First Business Operating System for MSMEs

An intelligent multi-agent business operating system designed for **Micro, Small & Medium Enterprises (MSMEs)**.  
Built to automate billing, inventory, CRM, accounting, and financial insights using a network of AI agents coordinated by a central orchestrator.

> Privacy-first • Offline-first • Model-agnostic • India-built

---

# Vision

Traditional MSME software only stores data.

**MSME AI Platform** goes beyond that.

It thinks, plans, automates, requests approval when needed, and helps businesses grow while keeping business data local and secure.

---

# Core Features

## Multi-Agent AI Architecture

A central **Orchestrator Agent** routes tasks to specialized agents:

- Billing Agent
- Inventory Agent
- Accounting Agent
- CRM Agent
- Credit Agent
- HR Agent *(planned / expandable)*

Each agent has its own responsibilities, tools, memory, and workflows.

---

## Billing & Invoicing

- GST invoice generation
- PDF invoice creation
- Automatic tax calculation
- Payment reminders
- Billing analytics
- Approval workflow before sending invoices

---

## Inventory Management

- Real-time stock tracking
- Automatic stock deduction from sales
- Low-stock alerts
- Reorder suggestions
- Purchase approval workflows

---

## CRM & Customer Growth

- Automatic customer database from invoices
- Purchase history tracking
- Inactive customer detection
- Campaign suggestions
- Customer segmentation

---

## Accounting Intelligence

- Revenue analytics
- KPI dashboard data
- Sales trends
- Profit estimation
- Top-selling products

---

## Credit Intelligence

- Business credit scoring
- Loan eligibility checks
- Financial health insights
- Growth readiness indicators

---

## Human-in-the-Loop (HITL)

Critical actions pause for approval:

- Sending invoices
- Purchase orders
- Bulk campaigns
- Loan requests
- Financial operations

Owner reviews the request, approves or rejects it, and the agent resumes execution.

---

# Tech Stack

## Frontend

- React
- TypeScript
- Tailwind CSS
- Framer Motion
- Three.js
- Recharts

## Backend

- FastAPI
- Python 3.11
- SQLite
- SQLAlchemy
- WebSockets

## AI Layer

- LangGraph
- CrewAI
- LangChain
- ChromaDB

## Deployment

- Tauri Desktop App
- Web Dashboard
- Offline-first Local Runtime

---

# Project Structure

```bash
frontend/
  Web-dashboard/

backend/
  agents/
    orchestrator.py
    billing_agent.py
    inventory_agent.py
    crm_agent.py
    accounting_agent.py
    credit_agent.py

  core/
    db.py
    watcher.py
    scheduler.py
    ws_manager.py

  modules/
    billing/
    inventory/
    accounting/
    crm/
    credit/