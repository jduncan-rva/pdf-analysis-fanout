# Operating Instructions

- Execute tasks methodically with deep reasoning, root cause analysis, and rigorous verification.
- Verify all file edits and test runs before marking tasks complete.

## Communication Protocol
When responding to incoming messages from users or other agents:
1. If the message metadata includes `thread_id` and/or `channel`:
   Always reply targeting the thread so it appears in the Web Chat:
   ```bash
   scion message --thread-id "<thread_id>" --channel "<channel>" "<your response>"
   ```
2. If responding directly to an agent or user DM:
   ```bash
   scion message @<recipient> "<your response>"
   ```
