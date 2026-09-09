# Financial Audit & Reconciliation Rules

## 1. Tolerance Thresholds
- **Immaterial Tolerance**: Discrepancies <= $0.05 are classified as `EXACT_MATCH` (cents precision).
- **Rounding Tolerance**: Discrepancies > $0.05 and <= $1.00 are classified as `ROUNDING_VARIANCE`.
- **Material Threshold**: Any discrepancy > $100.00 or > 1.0% of line total MUST be flagged with severity `HIGH` or `CRITICAL`.

## 2. Tax & Income Reconciliation
- **Wages & Compensation**: Form 1040 Line 1z must reconcile with sum(W-2 Box 1) + sum(1099-NEC Box 1).
- **Federal Withholding**: Form 1040 Line 25d must match sum(W-2 Box 2) + sum(1099 Box 4).
- **Interest Income**: Form 1040 Line 2b must match sum(1099-INT Box 1).

## 3. Commercial Accounts Payable & Receivable
- **Invoice Line Sum**: `Sum(Line Items) + Taxes + Shipping - Discounts == Total Due`.
- **Payment Clearing**: Remittance voucher amount must match bank transaction within 5 business days.

## 4. Anomaly Severity Classification
- **INFO**: Exact match or standard timing difference.
- **WARNING**: Rounding or non-critical documentation omission.
- **ERROR / CRITICAL**: Direct mismatch on bottom-line numbers, missing corroboration, or unsigned filings.
