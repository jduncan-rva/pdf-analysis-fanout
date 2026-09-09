# Agent Messaging and Chat Responses

When you receive a message from the user or orchestration system:
1. Check the message envelope for `thread_id` and `channel`.
2. If `thread_id` is present, you MUST reply using `scion message` with `--thread-id` and `--channel` so your response appears in the Web Chat thread:
   ```bash
   scion message --thread-id "<thread_id>" --channel "<channel>" "<your response>"
   ```
   For example:
   ```bash
   scion message --thread-id "4310f489-0e5d-4b3d-9ad0-8d3dfb8a6005" --channel web "Acknowledging receipt of your request."
   ```
3. If no thread_id is present, or if sending a 1-on-1 direct message:
   ```bash
   scion message @<recipient> "<your response>"
   ```
4. Always send a confirmation response when receiving a task, and report status upon completion.
