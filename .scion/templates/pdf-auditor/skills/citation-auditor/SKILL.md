---
name: citation-auditor
description: Verify claims against ground-truth document sources, audit page references, detect hallucinations, and generate traceable citations.
---

# Citation Auditor Skill

This skill ensures that every fact, numerical value, risk statement, and conclusion asserted in synthesized reports is strictly grounded in and cited against source document extractions.

## Guiding Principles
1. **Zero Unverified Claims**: Never state a financial figure, percentage, dates, or compliance assertion without linking to its primary source page.
2. **Ground Truth Verification**: Compare extracted statements against the raw text chunks in `/workspace/staging/<doc_id>/`.
3. **Traceable Notation**: Format citations using standard markdown footnote format `[^<doc_id>:p<page_num>]`.
4. **Hallucination Detection**: Flag any statement that extrapolates beyond the explicitly extracted text or table data.

---

## Audit Verification Steps

### Step 1: Claim Extraction
Parse candidate statements and compile a claims manifest:
- Claim Subject (e.g., "Q3 Operating Margin")
- Stated Value (e.g., "24.5%")
- Cited Source (`doc_id` and `page_number`)

### Step 2: Source Text Verification
Search `/workspace/staging/<doc_id>/` for matching strings or tabular cells:
1. Exact string match -> Confidence `1.0` (VERIFIED).
2. Semantic paraphrase with exact numerical match -> Confidence `0.9` (VERIFIED).
3. Derived calculation (e.g. sum of two rows) -> Confidence `0.85` (VERIFIED_DERIVED).
4. No source match found -> Confidence `0.0` (UNVERIFIED_HALLUCINATION).

### Step 3: Synthesis & Footnote Generation
Attach verified footnotes to the final report:

```markdown
Net operating income rose to **$4.2M** in fiscal year 2025[^annual_report:p14], representing a 15% increase year-over-year[^annual_report:p15].
```
