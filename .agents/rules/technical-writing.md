# Technical Writing Workspace Rules

When writing or editing markdown documentation (`.md`) files in this repository, always adhere to the following standards:

## Tone & Style
- Use concise, active-voice, developer-oriented phrasing.
- Avoid vague placeholders; use actual paths and symbol names found in the repo (e.g., `generate_pdf.py`, `infra/`, `cloud_functions/`).
- Focus on clarity, maintainability, and actionable instructions.

## Markdown Guidelines
- Always include syntax highlighting tags for code blocks (`python`, `bash`, `json`, `hcl`, `mermaid`).
- Use GitHub Flavored Markdown alerts (`> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]`) instead of bold plain-text warnings.
- Keep table columns aligned and clean.

## Source Verification
- Do not make assumptions about environment variables, script flags, or function parameters. Verify them in the codebase before updating documentation.
