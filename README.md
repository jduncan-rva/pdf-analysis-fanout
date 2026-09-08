# PDF Analysis Fanout System (GCP + GKE Autopilot)

A high-scale, two-stage document processing and semantic analysis pipeline designed for processing millions of financial PDFs (bank statements, invoices, tax forms, structured documents).

---

## 🏛️ Architecture Overview

```
[ Upload PDF ] ──────> Ingest GCS Bucket (`gs://${PROJECT}-pdf-ingest`)
                              │
                              ▼ (Eventarc / Cloud Storage Event)
                      Cloud Function (Gen2)
                              │
                              ▼ (Trigger HTTP API)
                      GKE Web Application (FastAPI + SQLite FTS5)
                              │
                              ▼ (Spawn K8s Job)
             ┌──────────────────────────────────────────────┐
             │ Stage 1: Ingest Job (PyMuPDF Fast Extractor) │
             │ • Extracts full text & metadata in ~20ms      │
             │ • Saves raw metadata JSON to Data GCS bucket │
             │ • POSTs to Webapp `/api/ingest/webhook`      │
             └──────────────────────────────────────────────┘
                              │
                              ▼
             Indexed into SQLite FTS5 (BM25 Search)
                              │
               [ User Searches in Web UI & Clicks "Analyze" ]
                              │
                              ▼ (Spawn K8s Job)
             ┌──────────────────────────────────────────────┐
             │ Stage 2: Deep Analysis (Antigravity Agent)   │
             │ • Converts PDF pages to high-res images      │
             │ • Multimodal LLM extracts bound JSON schema  │
             │ • Saves structured report to Data GCS bucket │
             │ • POSTs results to Webapp `/api/analyze/*`   │
             └──────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
pdf-analysis-fanout/
├── webapp/                      # FastAPI Web Server + SQLite FTS5
│   ├── app.py                  # API routes, webhooks, and UI rendering
│   ├── database.py             # SQLite DB schema, BM25 FTS5 search queries
│   ├── k8s_manager.py          # Spawns Ingest and Analysis Jobs in GKE
│   ├── templates/index.html    # Web UI template
│   ├── static/                 # Styles & client-side interaction script
│   ├── Dockerfile
│   └── requirements.txt
├── jobs/
│   ├── ingest/                 # Stage 1: Fast PyMuPDF Ingestion Job
│   │   ├── run_ingest.py       # Heuristic extraction + webhook dispatch
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── analysis/               # Stage 2: Antigravity Multimodal Analysis Job
│       ├── run_analysis.py     # Gemini Vision + structured JSON extraction
│       ├── Dockerfile
│       └── requirements.txt
├── cloud_functions/
│   └── gcs_trigger/            # Cloud Function triggered on PDF upload
│       ├── main.py
│       └── requirements.txt
├── infra/
│   ├── k8s/                    # Kubernetes manifests
│   │   ├── rbac.yaml           # ServiceAccount & Roles for Job creation
│   │   ├── pvc.yaml            # Persistent volume for SQLite DB
│   │   └── webapp.yaml         # Deployment & LoadBalancer Service
│   └── deploy.sh               # Deployment automation script
└── tests/
    └── test_database.py        # FTS5 and BM25 ranking tests
```

---

## 🚀 Deployment to GCP & GKE Autopilot

Make sure you have an active `gcloud` login and project configured:

```bash
# 1. Review environment variables or defaults
export REGION="us-central1"
export CLUSTER_NAME="pdf-fanout-cluster"

# 2. Run the deployment script
chmod +x infra/deploy.sh
./infra/deploy.sh
```

---

## 🧪 Local Testing

You can run the web application locally without Kubernetes:

```bash
cd webapp
pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.
