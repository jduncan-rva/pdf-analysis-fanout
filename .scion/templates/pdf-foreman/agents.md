# Foreman Operating Instructions

When managing a PDF fanout job:
- Leverage the `foreman-fanout-orchestration` skill for dispatch state and failure recovery protocols.
- Maintain a local state file at `/workspace/.foreman-state.json` recording assigned chunks, active agents, and completed outputs.
- Dispatch workers in manageable batches (e.g., 3-5 concurrent agents).
- Verify that every worker writes valid JSON schema output before marking its task complete.
- Use `citation-auditor` skill rules to ensure the final report footnotes map accurately to source chunks.
