# Citation Style Guide & Notation Rules

## Footnote Format
Always use the standardized bracketed notation for in-text citations:
`[^<document_id>:p<page_number>]` or `[^<document_id>:p<start_page>-p<end_page>]`

### Examples
- Single page reference: `[^annual_financials_2026:p12]`
- Multi-page range: `[^compliance_audit_2026:p18-p20]`
- Table specific: `[^annual_financials_2026:p14:table_02]`

## Footnote Reference Block
At the end of the markdown document, provide complete reference expansions:

```markdown
---
## References & Verified Sources

[^annual_financials_2026:p12]: `annual_financial_report.pdf`, Page 12, Section "Balance Sheet & Income Statement", Line Item: "Total Current Assets".
[^annual_financials_2026:p14:table_02]: `annual_financial_report.pdf`, Page 14, Table "Statement of Cash Flows".
[^compliance_audit_2026:p18-p20]: `regulatory_compliance_audit.pdf`, Pages 18-20, Section "Security Controls & Incident Logs".
```
