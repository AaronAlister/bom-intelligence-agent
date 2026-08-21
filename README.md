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
