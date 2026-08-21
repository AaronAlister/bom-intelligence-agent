````markdown
# BOM Intelligence Agent

An agentic engineering intelligence platform that transforms Bill of Materials (BOM) data into actionable insights for engineering and procurement teams.

## What It Does

- **BOM Ingestion** – Upload, validate, preprocess, and persist BOM data.
- **Component Intelligence** – Enrich components with manufacturer, category, package, lifecycle, and availability information.
- **Risk Intelligence** – Analyze component and BOM-level risk across lifecycle and availability factors.
- **Lifecycle Intelligence** – Track Active, NRND, EOL, Obsolete, and Unknown component states.
- **Alternative Matching** – Discover and rank potential replacement components using compatibility, package, manufacturer, lifecycle, and availability signals.
- **Document Intelligence** – Process technical documents and PDFs through a RAG pipeline for retrieval-based analysis.
- **Agentic Orchestration** – Coordinate multiple intelligence services into unified workflows.
- **Reports** – Generate consolidated BOM intelligence reports with risk summaries, top-risk components, drivers, and recommendations.

## Architecture

```text
BOM Upload
    ↓
Validation & Preprocessing
    ↓
Component Catalog
    ↓
┌────────────┬────────────┬──────────────┐
│    Risk    │ Lifecycle  │ Availability │
└────────────┴────────────┴──────────────┘
                ↓
       Alternative Matching
                ↓
          Document / RAG
                ↓
       Intelligence Report
```
````

Tech Stack

Backend: Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic

AI / Intelligence: OpenAI SDK, LangGraph, RAG, embeddings, vector search

Infrastructure: Redis, Celery, Qdrant

Frontend: React, TypeScript, Vite

Testing: pytest, pytest-asyncio, Ruff, TypeScript

Project Structure
bom-intelligence-agent/
├── backend/ # FastAPI backend and intelligence services
├── frontend/ # React + TypeScript dashboard
├── migrations/ # Database migrations
├── infra/ # Infrastructure configuration
├── scripts/ # Utility scripts
├── worker/ # Background task workers
├── pyproject.toml
└── README.md
Testing

Run the backend test suite:

python -m pytest backend/tests -q

Current test suite:

663 tests passing

Build the frontend:

cd frontend
npm run build
Status

The core platform is feature-complete, including BOM ingestion, component intelligence, risk analysis, lifecycle intelligence, alternative matching, RAG/document processing, agentic orchestration, and reporting.
