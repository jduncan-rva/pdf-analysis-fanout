# Agent Messaging and Chat Responses

When you receive a message from the user or orchestration system:
1. Extract the message fields from the envelope:
   - `<recipient>`: from `sender` or `metadata.mention_source` (e.g. `user:Jamie Duncan` or `@<agent-name>`).
   - `<channel>`: from `channel` (e.g. `web`).
   - `<thread_id>`: from `thread_id` (e.g. `03c11f33-f6f5-4f57-926c-dfb20c656665`).
2. Reply directly to the sender in the thread using `scion message`:
   ```bash
   scion message "<recipient>" "<your response>" --channel "<channel>" --thread-id "<thread_id>"
   ```
   For example:
   ```bash
   scion message "user:Jamie Duncan" "Confirmed. I received your message and am ready to proceed." --channel "web" --thread-id "03c11f33-f6f5-4f57-926c-dfb20c656665"
   ```
   If `channel` or `thread_id` are not present in the incoming envelope:
   ```bash
   scion message "<recipient>" "<your response>"
   ```
3. If responding directly to another agent outside a thread:
   ```bash
   scion message @<agent-name> "<your response>"
   ```
4. Always send a confirmation response when receiving a task, and report status upon completion.

