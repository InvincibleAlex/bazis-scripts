# Architecture and extension contract

`MCP stdio client → Python MCP SDK → atomic file queue → embedded Node 8 listener → BAZIS API`.

No public HTTP endpoint, cloud service or OpenAI API key is needed for this local connection.
The external Python environment is independent of the old embedded JavaScript engine.

Protocol 1 request: `protocol`, random lowercase-hex `id`, local `token`, target `session_id`,
`method`, object `params`, `created_at_ms`, `deadline_ms`. A response includes `id`, `session_id`,
`ok`, and `result` or `error`. All success results include `model_token`, `request_id`, `session_id`.
Never send the local token in tool results or commit it to a repository.

The listener claims `inbox/<id>.json` by moving it to `processing/`. It validates identity, session,
deadline and cancellation, then writes `journal/<id>.json` with state `started` before dispatch.
It publishes an atomic response to `outbox/`, then records completion. A leftover `started` journal
means the outcome is uncertain, not that the command is safe to repeat. Requests from old sessions
are rejected. Leftover processing files are never replayed automatically after restart.

Since 0.1.1 the MCP SDK server lifespan renews `client-heartbeat.json` every two seconds.
It is authenticated with the same local token and bound to the current BAZIS session. The
listener checks its age (seven-second lease) and updates `Action.Hint` only on state transitions.
The native hint icon/HintKind is not set. A recently authenticated request also indicates
presence for seven seconds. `status.json.mcp_client_connected` reports this reverse direction;
the outer `bazis_status.connected` continues to report whether the BAZIS listener is reachable.
Graceful server shutdown removes only the heartbeat belonging to its own client ID.

Snapshots expose data only. Getters for known properties are isolated by try/catch. Geometry blobs,
credentials, arbitrary object traversal and direct generic method invocation are not exposed.
Traversal is bounded to 50000 objects / 50 hierarchy levels, with 500-item pages.

To add a command:

1. Verify the exact legacy BAZIS API signature against its docs and installed diagnostic.
2. Add a bounded handler with input validation before any mutation.
3. For edits, require model token and edit permission; validate handles and target overlap.
4. Add a typed MCP tool and appropriate read-only/destructive annotations.
5. Test malformed input, native failure/rollback, stale handles and deadline behavior.
6. Record native validation separately from mock results; increment version for a release.

The project currently uses MCP SDK 1.26.0. The embedded listener deliberately uses ES5 syntax
and Node 8-compatible file/crypto APIs. Modern MCP dependencies never run inside BAZIS.
