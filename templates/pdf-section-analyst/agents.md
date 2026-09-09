# Section Analyst Operating Instructions

- Always include exact document ID and page number for every assertion extracted.
- Follow the `financial-reconciliation` skill for categorizing anomalies (e.g. `EXACT_MATCH`, `UNRECONCILED_MISMATCH`).
- Write output directly to `/workspace/output/<target_id>.json` and alert `@pdf-foreman`.
