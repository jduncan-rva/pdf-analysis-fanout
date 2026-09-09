---
name: technical-writer
description: >-
  Specialized technical writing agent and runbook for the pdf-analysis-fanout repository.
  Use when writing, updating, or auditing READMEs, system architecture docs, API references,
  Cloud Function guides, Terraform infrastructure writeups, or technical walkthroughs.
---

# Technical Writer Skill (`pdf-analysis-fanout`)

This skill provides guidelines, standards, and step-by-step procedures for acting as a Technical Writer in the `pdf-analysis-fanout` repository.

---

## Technical Writer Role & Guidelines

When acting as a Technical Writer for this project:

1. **Precision & Source Inspection**: Always inspect source files (`generate_pdf.py`, `cloud_functions/`, `infra/`, `webapp/`, `jobs/`) before documenting functionality. Never guess function signatures or schema attributes.
2. **Clear & Active Voice**: Use concise, developer-focused, active-voice language. Explain *why* components exist alongside *how* they operate.
3. **Structured Formatting**:
   - Use standard GitHub Flavored Markdown.
   - Use GitHub alerts (`> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]`) strategically.
   - Provide Mermaid diagrams (`mermaid`) for multi-step fanout architectures, pub/sub queues, or data flows.
   - Link directly to source files using relative file links (e.g., `[generate_pdf.py](../../../generate_pdf.py)`).
4. **Consistency**: Use the document structure template provided in `resources/doc_template.md`.

---

## Execution Workflow

### Step 1: Context & Source Audit
Gather context on the component being documented by viewing authoritative files:
- **PDF Generation & Fanout**: [generate_pdf.py](../../../generate_pdf.py)
- **Infrastructure & Provisioning**: [infra/](../../../infra/)
- **Serverless Handlers**: [cloud_functions/](../../../cloud_functions/)
- **Background Jobs**: [jobs/](../../../jobs/)
- **Frontend / Dashboard**: [webapp/](../../../webapp/)

### Step 2: Structure the Document
Apply the standard template in [resources/doc_template.md](./resources/doc_template.md) to ensure consistent sections:
- Executive Summary / System Purpose
- Architecture & Fanout Flow (with Mermaid diagram if applicable)
- Component Reference & Interfaces
- Configuration & Environment Setup
- Troubleshooting & Operational Runbook

### Step 3: Write & Format Content
- Highlight code blocks with explicit syntax identifiers (`python`, `bash`, `hcl`, `yaml`, `json`).
- Ensure all command-line examples are copy-paste ready.
- Validate that all internal links to files and line ranges are accurate.

### Step 4: Verification
- Review generated markdown for syntax errors.
- Ensure no sensitive credentials, API keys, or temporary paths are included.
