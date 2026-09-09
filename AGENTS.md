# PDF Analysis Fanout: Agent Instructions & Architecture Guide

## Overview

`pdf-analysis-fanout` is a distributed, two-stage document processing and semantic analysis pipeline designed for processing large volumes of financial PDFs (e.g. bank statements, invoices, tax forms, structured documents) on Google Cloud Platform and Google Kubernetes Engine (GKE Autopilot).

This repository serves two primary roles:
1. **Application Codebase:** Implements the FastAPI web application, PyMuPDF fast ingestion jobs, multimodal structured JSON extraction jobs (using Gemini/Antigravity), and Kubernetes/Cloud deployment manifests.
2. **Scion Project:** Represents a registered Scion project (`PDF Fanout Analysis Demo` / `pdf-fanout-analysis-demo`) orchestrated by a centralized Scion Hub and executed by runtime brokers across GKE clusters.

---

## 🏛️ System Architecture

The pipeline processes documents asynchronously in two distinct stages:

```
[ Upload PDF ] ──────> Ingest GCS Bucket (`gs://${PROJECT}-pdf-ingest`)
                              │
                              ▼ (Eventarc / Cloud Storage Event)
                      Cloud Function (Gen2: `cloud_functions/gcs_trigger`)
                              │
                              ▼ (POST /api/ingest/trigger)
                      GKE Web Application (FastAPI: `webapp/app.py`)
                              │
                              ▼ (Spawns K8s Ingest Job: `jobs/ingest`)
             ┌──────────────────────────────────────────────┐
             │ Stage 1: Ingest Job (PyMuPDF Fast Extractor) │
             │ • Extracts full text & metadata in ~20ms      │
             │ • Saves raw metadata JSON to Data GCS bucket │
             │ • POSTs to Webapp `/api/ingest/webhook`      │
             └──────────────────────────────────────────────┘
                              │
                              ▼
             Indexed into SQLite FTS5 (BM25 Full-Text Search)
                              │
               [ User Searches in Web UI & Clicks "Analyze" ]
                              │
                              ▼ (POST /api/analyze/trigger)
             ┌──────────────────────────────────────────────┐
             │ Stage 2: Deep Analysis (Antigravity Agent)   │
             │ • Converts PDF pages to high-res images      │
             │ • Multimodal Gemini extracts bound JSON schema│
             │ • Saves structured report to Data GCS bucket │
             │ • POSTs results to Webapp `/api/analyze/*`   │
             └──────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
pdf-analysis-fanout/
├── webapp/                      # FastAPI Web Application & API Layer
│   ├── app.py                  # API routes, webhooks, and UI rendering
│   ├── database.py             # SQLite DB schema, BM25 FTS5 search queries
│   ├── k8s_manager.py          # Spawns Ingest and Analysis Jobs in GKE
│   ├── templates/index.html    # Web UI template
│   ├── static/                 # Styles & client-side interaction script
│   ├── Dockerfile              # Webapp container build
│   └── requirements.txt        # FastAPI, Uvicorn, SQLite dependencies
├── jobs/
│   ├── ingest/                 # Stage 1: Fast PyMuPDF Ingestion Job
│   │   ├── run_ingest.py       # Heuristic text extraction + webhook dispatch
│   │   ├── Dockerfile
│   │   └── requirements.txt    # PyMuPDF (fitz), google-cloud-storage
│   └── analysis/               # Stage 2: Multimodal Structured Extraction Job
│       ├── run_analysis.py     # Gemini Vision + structured JSON extraction
│       ├── Dockerfile
│       └── requirements.txt    # google-genai / vertexai, pydantic, Pillow
├── cloud_functions/
│   └── gcs_trigger/            # Cloud Function triggered on PDF upload
│       ├── main.py             # Eventarc GCS notification handler
│       └── requirements.txt
├── infra/
│   ├── k8s/                    # Kubernetes manifests
│   │   ├── rbac.yaml           # ServiceAccount & Roles for Job creation
│   │   ├── pvc.yaml            # Persistent volume for SQLite DB
│   │   └── webapp.yaml         # Deployment & LoadBalancer Service
│   └── deploy.sh               # GCP/GKE automated deployment script
├── sample_pdfs/                # Test PDFs for ingestion & validation
├── tests/
│   └── test_database.py        # FTS5 and BM25 ranking tests
├── .scion/                     # Scion project metadata and agent state
└── AGENTS.md                   # Agent guidelines and project overview (this file)
```

---

## 🤖 Role as a Scion Project

This repository is linked to a Scion Hosted Hub as a registered project. LLM-based autonomous agents (e.g. `foreman1`, workers) are dispatched into this repository to inspect, build, test, and maintain the codebase.

### Key Scion Configurations:
- **Project Name:** `PDF Fanout Analysis Demo`
- **Project Slug:** `pdf-fanout-analysis-demo`
- **Git Remote:** `https://github.com/jduncan-rva/pdf-analysis-fanout.git`
- **Agent Runtime:** GKE Autopilot (`scion-agents` cluster, `scion-agents` namespace)
- **Harness & Auth:** `antigravity` harness using Vertex AI ADC via Hub service account impersonation (`pdf-fanout-gsa@gke-llm-testing-env.iam.gserviceaccount.com`).
- **Workspace Strategy:** Per-agent isolated clone (`clone-per-agent`).

### Interacting with Scion Agents:
- **Web Chat Dashboard:** Navigate to `http://localhost:8080/chat` to access project spaces, collaborative threads, and 1-on-1 agent DMs.
- **Check running agents:** `scion list --project "PDF Fanout Analysis Demo"`
- **Inspect live agent terminal:** `scion look <agent-name> --project "PDF Fanout Analysis Demo"`
- **Attach interactively:** `scion attach <agent-name> --project "PDF Fanout Analysis Demo"`
- **Send instruction message:** `scion message @<agent-name> "instruction"`
- **Full Chat Guide:** See [CHAT_INTERACTION_GUIDE.md](file:///Users/jamieduncan/Code/pdf-analysis-fanout/CHAT_INTERACTION_GUIDE.md) for full details on `@-mentions`, `ask_user` loops, rich diffs, and desktop federation via Google's A2A protocol.

---

## 🛠️ Development & Testing Guidelines

### Local Testing Without Kubernetes
You can run the web server and execute unit tests locally:

```bash
# 1. Install webapp dependencies
pip install -r webapp/requirements.txt

# 2. Run unit tests
pytest tests/ -v

# 3. Start the FastAPI development server
uvicorn webapp.app:app --host 0.0.0.0 --port 8000 --reload
```

### Ingestion & Analysis Jobs Testing
- Ingestion jobs extract raw text and metadata quickly with PyMuPDF.
- Analysis jobs process documents using Vertex AI / Gemini Multimodal API. Ensure `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` are configured in your environment.

### Code Style & Commit Rules
- Keep Python code clean, modular, and typed where appropriate.
- Do not commit generated SQLite databases (`*.db`), scratch PDFs, or agent orchestration state files to Git.
- Always verify tests pass (`pytest tests/`) before pushing changes or completing agent assignments.
