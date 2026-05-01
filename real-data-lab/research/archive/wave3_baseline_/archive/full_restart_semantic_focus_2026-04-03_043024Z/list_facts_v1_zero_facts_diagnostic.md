# Why `list_facts_v1` sometimes showed **0** facts (Real Data Lab)

Spirl application source is **not** in `SPIRAL-RESEARCH`; this note ties **your log** to **likely server/runtime causes** and **harness behavior**.

## What the log proves

From `real_data_lab_execution_log.jsonl` for project `f660d6ad-6cf5-486d-928a-93752ef916b4`:

| Time (UTC) | `total_facts_listed_in_project` | Context |
|------------|----------------------------------|---------|
| ~22:08–22:13 | **106** | `project_seed_audit` after Phase 2 resumed |
| ~22:38 | **0** | Same `project_id`, immediate `baseline_validation_failed` |
| ~23:04 | **141** | Same `project_id`, healthy audit again |

Between those windows, the log records **`WinError 10061`** (connection refused to `localhost:8000`) on MCP upserts. So the Spirl process **was not reliably up**, or the client hit a **different** listener.

**Conclusion:** The “0 facts” snapshot is overwhelmingly consistent with **server / datastore / process boundary**, not with Phase 1 “creating the project wrong.” Phase 1 already logged a connected SKF subgraph (`graph_verified`).

## Likely backend-side explanations (check on the Spirl repo / deployment)

1. **Empty or reset database** — Server restart with a fresh SQLite/Postgres volume, `migrate` on new file, or test teardown.
2. **In-memory store** — If facts live only in process memory, **any** restart yields **0** facts until re-import.
3. **Multiple workers / instances** — Sticky sessions not used: one request hits a worker with data, another hits a cold worker (depends on how Spirl stores state).
4. **Wrong DB URL in env** — Same `localhost:8000` URL after a compose restart can point at a **new** container with an **empty** DB while the old volume was not attached.
5. **Auth / tenant filter** — Less common, but if `list_facts_v1` filters by token scope and the token maps to “no access,” you could get an empty list (verify in Spirl code).

## Harness-side caveat (fixed in scripts)

`paper3_phase2_mcp_run._tool_result_as_dict` used to turn any **non-dict** JSON root (e.g. a **bare array**) into `{}`, so `facts` became `[]` **without** an MCP error. If a Spirl version ever returns `list_facts_v1` as a top-level JSON array, the client could **falsely** report 0 facts. The shared helper now treats a list of objects as `{"facts": [...]}`.

**If you still see 0** after this fix: treat it as **trust the server** (empty DB or filter) and confirm with:

- Direct HTTP/MCP call to `list_facts_v1` with the same `project_id`
- Spirl DB row counts for that `project_id`
- Server logs at the exact timestamp of the audit line

## Operator checklist before long Phase 2 runs

1. Spirl stays up for the **entire** run (no sleep, no compose stop).
2. After **any** restart, run `real_data_lab_phase2_mcp_run.py --precheck-only` and confirm `total_facts_listed_in_project` matches expectation (~79 SKF keys + research rows already injected).
3. Prefer a **persistent** database volume for the dev stack.
4. If using multiple replicas, confirm Spirl is **single-writer** or **shared** storage for facts.
