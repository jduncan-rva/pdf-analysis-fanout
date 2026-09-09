---
name: pdf-layout-extractor
description: Extract clean layout, text chunks, tables, and metadata from PDF files using PyMuPDF and OCR heuristics.
---

# PDF Layout & Text Extractor Skill

This skill provides comprehensive instructions, conventions, and helper tools for converting unstructured or semi-structured PDF documents into normalized JSON chunks and Markdown representations.

## Objectives
1. **Accurate Text & Layout Extraction**: Preserve section hierarchy, headers, paragraphs, lists, and footers.
2. **Table Normalization**: Extract tabular data into structured 2D matrices / JSON dictionaries rather than flattened text lines.
3. **Citation-Ready Chunking**: Tag every chunk with exact `doc_id`, `page_number`, `bounding_box` (if available), and `section_title`.
4. **Resilience**: Handle multi-column layouts, rotated pages, scanned artifacts, and corrupted text streams gracefully.

---

## Workflow & Protocol

### Step 1: Document Inspection
Before performing full extraction, inspect document metadata:
- Page count
- Embedded fonts and text stream availability (searchable text vs scanned images)
- Logical table of contents or outline markers

```bash
# Example quick inspection via python or pdfinfo
python3 -c "import fitz; doc = fitz.open('/workspace/doc.pdf'); print(f'Pages: {len(doc)}, TOC: {doc.get_toc()}')"
```

### Step 2: Chunk Partitioning
Divide the document into logical chunks based on:
1. **Section Boundaries**: Split on major headings (`#`, `##`, capitalized headers).
2. **Page Boundaries**: Maintain contiguous page spans (e.g., Pages 1–3: Executive Summary).
3. **Table Isolation**: Extract tables as standalone semantic objects attached to their parent section.

### Step 3: Structured JSON Output
Write extracted chunks to `/workspace/staging/<doc_id>/chunk_<index>.json` adhering to `references/schema.json`:

```json
{
  "document_id": "annual_report_2026",
  "chunk_id": "chunk_001",
  "page_start": 1,
  "page_end": 2,
  "section_title": "Consolidated Financial Highlights",
  "content_markdown": "## Consolidated Financial Highlights\n\nRevenue for Q4 reached $14.2M...",
  "tables": [
    {
      "table_id": "table_q4_summary",
      "headers": ["Metric", "Q4 2025", "Q4 2026", "YoY Change"],
      "rows": [
        ["Total Revenue", "$11.8M", "$14.2M", "+20.3%"],
        ["Operating Income", "$2.1M", "$3.4M", "+61.9%"]
      ]
    }
  ],
  "metadata": {
    "word_count": 482,
    "has_tables": true,
    "confidence_score": 0.98
  }
}
```

---

## Handling Tricky Scenarios

| Scenario | Recommended Strategy |
|---|---|
| **Multi-Column Text** | Sort text blocks by vertical `y0` coordinate per column band before merging. |
| **Header / Footer Noise** | Detect repeating top/bottom margin text across pages and strip from body chunks. |
| **Embedded Images / Scans** | If text stream is empty, flag for OCR / Multimodal Gemini analysis. |
| **Merged Table Cells** | Unfold merged headers by propagating the parent header label down to child columns. |
