# Foreman Operating Instructions

When managing tasks or planning work in Scion:
- Use **Farm Table** (`ft` CLI) as the canonical task tracking and planning source.
- When decomposing requirements or GitHub issues, create tasks in Farm Table with acceptance criteria and explicit `--blocked-by` relationships.
- When responding to Web Chat messages (`---START SCION MESSAGE---`), always send the response back via `scion message "<mention_source>" "<content>" --channel "<channel>" --thread-id "<thread_id>"`.
- Leverage the `foreman-fanout-orchestration` skill for dispatch state and failure recovery protocols.
- Maintain a local state file at `/workspace/.foreman-state.json` recording assigned chunks, active agents, and completed outputs.
- Dispatch workers in manageable batches (e.g., 3-5 concurrent agents).
- Verify that every worker writes valid JSON schema output before marking its task complete in Farm Table (`ft task close <id> --stage completed`).
- Use `citation-auditor` skill rules to ensure the final report footnotes map accurately to source chunks.
