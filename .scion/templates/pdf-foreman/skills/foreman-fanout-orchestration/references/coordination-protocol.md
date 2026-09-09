# Foreman Coordination Protocol

## Worker State Machine
1. `QUEUED`: Worker definition created in state file.
2. `SPAWNING`: `scion create` and `scion start --notify` executed.
3. `RUNNING`: Worker actively executing harness instructions.
4. `NOTIFIED_COMPLETE`: Completion message received on Scion message bus.
5. `VERIFIED`: Output JSON validated against schema.
6. `PURGED`: Agent deleted via `scion delete` to free resources.
7. `FAILED`: Worker failed or timed out; re-enqueue chunk for retry.

## Retry Policy
- If a worker crashes or errors without emitting `/workspace/output/<target_id>.json`, retry once with fresh agent instance.
- If it fails twice, log warning in state file and proceed with partial results.
