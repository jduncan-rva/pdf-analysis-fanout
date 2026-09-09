---
name: financial-reconciliation
description: Cross-document financial analysis, ledger reconciliation, variance calculation, and anomaly detection across invoices, balance sheets, and tax documents.
---

# Financial Reconciliation Skill

This skill guides agents in performing rigorous, cross-document reconciliation of financial figures, transactions, tax filings, and ledger statements.

## Objectives
1. **Multi-Source Cross-Referencing**: Compare amounts across distinct source documents (e.g., Form 1040 vs W-2/1099, invoice vs bank remittance, balance sheet vs income statement).
2. **Variance Calculation**: Compute dollar and percentage differences between reported and audited amounts.
3. **Anomaly Classification**: Categorize discrepancies into standard auditing flags:
   - `EXACT_MATCH`: $0.00 difference.
   - `ROUNDING_VARIANCE`: Difference <= $1.00 due to integer/cents rounding.
   - `TIMING_DIFFERENCE`: Recognized in subsequent periods.
   - `UNRECONCILED_MISMATCH`: Material variance requiring investigation.
   - `MISSING_RECORD`: Item present in primary source but absent in secondary.
4. **Structured Reconciliation Output**: Generate machine-readable JSON records and formatted executive Markdown matrices.

---

## Reconciliation Workflow

### 1. Ingest Extracted Financial Records
Load structured chunks from `/workspace/staging/` or `/workspace/output/`. Extract line items with:
- Line item name / description
- Transaction dates
- Stated currency & amounts
- Exact document citation (doc ID + page number)

### 2. Match Pairs & Ledger Mapping
For every financial claim in Document A, search for corresponding corroborating entries in Document B:
```python
# Example comparison logic
variance = abs(source_amount - target_amount)
pct_variance = (variance / source_amount) * 100 if source_amount != 0 else 0.0
```

### 3. Apply Audit Rules
Consult `references/reconciliation-rules.md` for domain-specific checks:
- **IRS 1040 vs W-2**: Line 1a (Wages, salaries, tips) MUST equal the sum of Box 1 on all attached W-2s.
- **Invoice vs Bank Statement**: Net payable after discounts must match the settled wire/ACH amount.
- **Balance Sheet Equality**: `Total Assets == Total Liabilities + Shareholder Equity`.

### 4. Output Summary Matrix
Produce findings following `templates/reconciliation-matrix.md` and persist to `/workspace/output/reconciliation_<id>.json`.
