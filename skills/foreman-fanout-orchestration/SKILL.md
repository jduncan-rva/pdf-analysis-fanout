---
name: foreman-fanout-orchestration
description: Orchestrate parallel worker agent fleets with Scion CLI, manage document batches, track async completion events, and synthesize aggregate results.
---

# Foreman Fanout Orchestration Skill

This skill equips the foreman agent (`pdf-foreman`) with operational protocols and execution logic for driving multi-agent fanout pipelines on Scion.

## Principles of Foreman Orchestration
1. **Never Process Linearly**: The foreman coordinates, assigns tasks, and synthesizes results. Heavy extraction and granular analysis are delegated to worker agents.
2. **Managed Concurrency**: Dispatch agents in controlled concurrency waves (typically 3–5 parallel agents) to optimize host memory and API quotas.
3. **Event-Driven Non-Blocking Execution**: Launch agents with `--notify` or listen on Scion messaging events rather than running tight polling loops.
4. **State Persistence**: Track batch state, assigned documents, and worker health in `/workspace/.foreman-state.json`.
5. **Resource Reclamation**: Terminate and clean up completed worker agents (`scion delete <agent> --force`) once output artifacts are verified.

---

## Orchestration Lifecycle

```mermaid
sequenceDiagram
    participant F as PDF Foreman
    participant S as Scion CLI / Hub
    participant W as Worker Agent (Analyst)
    participant A as Audit Lead

    F->>F: Read manifest & scan PDFs
    F->>S: scion create worker-1 --type pdf-section-analyst
    F->>S: scion start worker-1 --notify
    Note over F: Yield execution (Awaiting notification)
    W->>W: Process chunk & write /output/
    W->>S: scion message @pdf-foreman "Completed"
    S->>F: Wakeup notification
    F->>F: Validate /workspace/output/worker-1.json
    F->>S: scion delete worker-1 --force
    F->>S: scion create auditor-1 --type pdf-auditor
    F->>S: scion start auditor-1
    A->>A: Generate final-synthesis-report.md
```

---

## Execution Commands

### 1. Provisioning a Worker
```bash
scion create extractor-01 "Extract /workspace/docs/financials.pdf" --type pdf-extractor
scion start extractor-01 --notify
```

### 2. State File Structure (`/workspace/.foreman-state.json`)
```json
{
  "batch_id": "pdf-batch-2026-09-09",
  "status": "IN_PROGRESS",
  "workers": {
    "extractor-01": {
      "type": "pdf-extractor",
      "target_file": "financials.pdf",
      "status": "COMPLETED",
      "output": "/workspace/staging/financials/"
    },
    "analyst-01": {
      "type": "pdf-section-analyst",
      "target_chunk": "/workspace/staging/financials/chunk_001.json",
      "status": "RUNNING"
    }
  }
}
```

### 3. Output Validation & Cleanup
Before cleaning up a worker, confirm its output JSON exists and is non-empty:
```bash
if [ -s "/workspace/output/analyst-01.json" ]; then
  scion delete analyst-01 --force
fi
```
