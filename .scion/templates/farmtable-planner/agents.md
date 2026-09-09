# Farm Table Planner Instructions

- Analyze requirements, PRDs, and GitHub issues thoroughly.
- Deconstruct high-level goals into atomic, testable tasks.
- Use `ft task create` with `-s accepted` to seed tasks in Farm Table.
- Establish explicit `--blocked-by` relationships to form an executable DAG.
- Validate that `ft task ready` returns only the initial wave of unblocked tasks.
- Send a complete summary of the generated DAG back to the user via `scion message "<mention_source>" "<summary>"`.
