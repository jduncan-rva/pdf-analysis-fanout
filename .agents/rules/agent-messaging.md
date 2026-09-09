# Agent Messaging and Chat Responses

When you receive a message from the user or orchestration system:
1. Extract the recipient from `sender` or `metadata.mention_source` (e.g. `user:<name>` or `@<agent-name>`).
2. Reply directly using `scion message`:
   ```bash
   scion message "<recipient>" "<your response>"
   ```
   For example:
   ```bash
   scion message "user:Jamie Duncan" "Acknowledging receipt of your request."
   ```
3. If responding directly to another agent:
   ```bash
   scion message @<agent-name> "<your response>"
   ```
4. Always send a confirmation response when receiving a task, and report status upon completion.

