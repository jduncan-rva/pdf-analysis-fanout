Deployment & Verification Walkthrough
The PDF Analysis Fanout Architecture is fully deployed to Google Cloud Platform (gke-llm-testing-env in us-central1) with automated two-stage function chaining.

Live System Endpoints & Resources
Resource	Value / Endpoint	Description
Web UI / Search Portal	http://35.223.231.166:8000	Live FastAPI Web Interface with BM25 Search & Document Inspector
Ingestion GCS Bucket	gs://gke-llm-testing-env-pdf-ingest	Drop zone where raw PDFs are uploaded
Data GCS Bucket	gs://gke-llm-testing-env-pdf-data	Extracted JSON metadata & deep analysis reports
GKE Autopilot Cluster	pdf-fanout-cluster (us-central1)	Auto-scaling Kubernetes cluster running jobs and web tier
Artifact Registry Repo	us-central1-docker.pkg.dev/gke-llm-testing-env/pdf-fanout-repo	Container registry housing webapp, ingest, and analysis images
Cloud Function 1 (Ingest Trigger)	pdf-ingest-trigger (us-central1)	Eventarc trigger listening to GCS PDF uploads
Cloud Function 2 (Analysis Trigger)	pdf-analysis-trigger (us-central1)	Eventarc trigger listening to raw metadata completion
End-to-End Automated Pipeline
graph TD
    User([Upload PDF]) -->|Uploads PDF| GCS_Ingest[(gs://...-pdf-ingest)]
    GCS_Ingest -->|Eventarc finalized| CF1[Cloud Function: pdf-ingest-trigger]
    CF1 -->|POST /api/ingest/trigger| Webapp[GKE Webapp: 35.223.231.166:8000]
    Webapp -->|Dispatches Job| K8s_Ingest[K8s Ingest Job: PyMuPDF Worker]
    K8s_Ingest -->|Saves Raw JSON| GCS_Data[(gs://...-pdf-data/extracted_metadata/)]
    K8s_Ingest -->|POST /api/ingest/webhook| Webapp
    Webapp -->|Indexes Document| SQLite[(SQLite FTS5 + BM25)]
    
    GCS_Data -->|Eventarc finalized| CF2[Cloud Function: pdf-analysis-trigger]
    CF2 -->|POST /api/analyze/trigger| Webapp
    Webapp -->|Dispatches Job| K8s_Analysis[K8s Analysis Job: Gemini Vision Worker]
    K8s_Analysis -->|Multimodal Extraction| VertexAI[Vertex AI / Gemini 2.5 Flash]
    K8s_Analysis -->|Saves Analysis Report| GCS_Data
    K8s_Analysis -->|POST /api/analyze/webhook| Webapp
    Webapp -->|Updates Status to ANALYZED| SQLite
Verified Documents in Corpus
Document	Type	Pages	Extraction Highlights
auto_pipeline_invoice.pdf	Invoice	1	Automatically chained via CF1 & CF2; 3 line items ($14,500.00 total) extracted.
chase_platinum_statement.pdf	Bank Statement	2	10 multi-line transactions with running balances and category classification.
irs_form_1040.pdf	Tax Return Form	2	70+ form fields, schedules, checkboxes, and taxpayer info mapped to structured schema.
irs_form_w9.pdf	Tax Request Form	6	Full text and entity indexing.
irs_form_1099_misc.pdf	Miscellaneous Info	6	Indexed into BM25 corpus and extracted.
sample_statement.pdf	Bank Statement	1	Balance summary & arithmetic reconciliation detection.
