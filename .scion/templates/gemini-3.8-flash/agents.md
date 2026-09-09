# Operating Instructions

- Execute tasks rapidly with structured outputs.
- Verify all file edits and test runs before marking tasks complete.

## Communication Protocol
When responding to incoming messages from users or other agents:
1. When responding to a user or mention in a thread, reply using:
   ```bash
   scion message "<sender>" "<your response>" --channel "<channel>" --thread-id "<thread_id>"
   ```
2. When messaging another agent directly:
   ```bash
   scion message @<agent-name> "<your response>"
   ```

