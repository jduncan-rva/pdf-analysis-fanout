# Scion Metrics & Telemetry: Architecture & Demo Guide

This guide explains how Scion metrics work under the hood and provides a step-by-step walkthrough for enabling, running, and querying metrics in this demo environment.

---

## 1. Metrics Architecture Overview

Scion employs a **two-tier metrics architecture** designed to bridge container-isolated agent executions with centralized operational observability:

```
┌──────────────────────────────────────────────────────────┐
│ Agent Container (Docker / Apple Virtualization / GKE)    │
│                                                          │
│  ┌───────────────────┐        ┌───────────────────────┐  │
│  │  Harness Process  │        │   sciontool (PID 1)   │  │
│  │ (AGY/Claude/etc.) │──hooks─▶ Telemetry Forwarder   │  │
│  └───────────────────┘        │ - PreToolUse/PostTool │  │
│                               │ - ModelStart/ModelEnd │  │
│                               │ - SessionStart/End    │  │
│                               └──────────┬────────────┘  │
└──────────────────────────────────────────┼───────────────┘
                                           │
                        POST /api/v1/agents/{id}/metrics
                        (X-Scion-Agent-Token)
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────┐
│ Scion Hub (State Server)                                 │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ REST Handlers (pkg/hub/handlers_agent_metrics.go)  │  │
│  └────────────────────────┬───────────────────────────┘  │
│                           │                              │
│                           ▼                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ SQLite / PostgreSQL (agent_session_metrics table)  │  │
│  └────────────────────────┬───────────────────────────┘  │
│                           │                              │
│                           ▼                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Aggregation APIs & Web Dashboard                   │  │
│  │ - GET /api/v1/projects/{id}/metrics/summary        │  │
│  │ - GET /api/v1/agents/{id}/metrics/summary          │  │
│  │ - GET /api/v1/metrics/dashboard                    │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Telemetry Pipeline Components
1. **Container Init & Hooks (`sciontool`)**:
   - `sciontool` runs as PID 1 inside the agent container.
   - Harnesses invoke `sciontool hook --dialect=<dialect>` on every tool use, prompt submission, model turn, and session termination.
   - The telemetry handler calculates token usage (`input`, `output`, `cached`, `reasoning`), counts tool invocations (`calls`, `success`, `error`), and tracks durations.
2. **Session Reporting**:
   - On `session-end`, `sciontool` constructs a `MetricsPayload` JSON object and sends it to the Hub: `POST /api/v1/agents/{agent_id}/metrics` authenticated with the ephemeral `X-Scion-Agent-Token`.
3. **Hub Ingestion & Aggregation**:
   - The Hub validates agent token scope, checks IDOR boundaries, and records the session into `agent_session_metrics`.
   - Dynamic SQL aggregations compute project and agent metrics:
     - `TotalSessions`, `TotalTokensInput`, `TotalTokensOutput`, `TotalTokensCached`, `TotalTokensReasoning`
     - `TotalToolCalls`, `AvgSessionDurationMs`
     - `MostUsedTools` (ranked list with call counts)
     - `MostUsedModels` (ranked list with call counts)

---

## 2. Configuration for Demo & Production

### A. Local / Demo Environment (Zero Cloud Dependencies)
To run metrics in a local demo without Google Cloud credentials, enable Hub metrics and local console telemetry in your template or settings:

```yaml
# In scion-agent.yaml or settings.yaml
telemetry:
  enabled: true
  hub:
    enabled: true
    report_interval: "10s"
  local:
    enabled: true
    console: true
```

### B. Hosted / Google Cloud Monitoring (Production & GKE)
In Google Cloud & GKE hosted environments, the Hub server initializes the Cloud Monitoring service (`pkg/hub/metrics_dashboard.go`) to query time-series metrics (`workload.googleapis.com/...`) for the Web UI Metrics Dashboard:

1. **Hub Settings (`~/.scion/settings.yaml` or GKE `scion-hub-settings` Secret)**:
   ```yaml
   gcp_project_id: "gke-llm-testing-env"
   telemetry:
     enabled: true
     cloud:
       enabled: true
       provider: gcp
       gcp_project_id: "gke-llm-testing-env"
       cloud_logging: true
     hub:
       enabled: true
       report_interval: "10s"
   ```

2. **Environment Variables (`scion-hub-env` ConfigMap / Deployment)**:
   ```yaml
   SCION_TELEMETRY_GCP_PROJECT_ID: "gke-llm-testing-env"
   SCION_GCP_PROJECT_ID: "gke-llm-testing-env"
   ```

3. **Required GCP IAM Roles** (bound to GKE Workload Identity SA `scion-hub-runner@<project>.iam.gserviceaccount.com`):
   - `roles/monitoring.viewer`: Queries Cloud Monitoring time series.
   - `roles/monitoring.metricWriter`: Writes OpenTelemetry metrics.
   - `roles/logging.logWriter`: Writes Cloud Logging entries.


---

## 3. Querying Metrics via REST API

### 1. Project Summary Metrics
Roll-up of all agents in the PDF fanout pipeline:
```bash
curl -s -H "Authorization: Bearer <AUTH_TOKEN>" \
  http://localhost:8080/api/v1/projects/<project_id>/metrics/summary | jq .
```
**Sample Response**:
```json
{
  "projectId": "proj-pdf-fanout",
  "totalSessions": 4,
  "totalTokensInput": 48200,
  "totalTokensOutput": 6120,
  "totalTokensCached": 12800,
  "totalTokensReasoning": 3400,
  "totalToolCalls": 37,
  "avgSessionDurationMs": 14200,
  "mostUsedTools": [
    {"name": "pdf_extractor", "count": 18},
    {"name": "view_file", "count": 12},
    {"name": "run_command", "count": 7}
  ],
  "mostUsedModels": [
    {"name": "gemini-2.5-pro", "count": 2},
    {"name": "gemini-2.5-flash", "count": 2}
  ]
}
```

### 2. Individual Agent Summary Metrics
Breakdown for a specific worker (e.g. `extractor-01`):
```bash
curl -s -H "Authorization: Bearer <AUTH_TOKEN>" \
  http://localhost:8080/api/v1/agents/<agent_id>/metrics/summary | jq .
```

### 3. Broker & Infrastructure Metrics
Hub internal health, broker authentication attempts, and GCP token brokering rates:
```bash
curl -s -H "Authorization: Bearer <AUTH_TOKEN>" \
  http://localhost:8080/api/v1/admin/metrics | jq .
```

---

## 4. Running the Demo Script

We provide an automated demonstration script `scripts/demo_metrics.sh` that simulates agent runs across the PDF fanout fleet and verifies metrics aggregation.

To run:
```bash
cd examples/pdf-analysis-fanout
chmod +x scripts/demo_metrics.sh
./scripts/demo_metrics.sh
```
