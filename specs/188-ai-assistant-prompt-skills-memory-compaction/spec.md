# Spec 188: AI Assistant Workspace MEMORY.md

## Status

Slices 188.0, 188.1, and 188.3 remain historical completed work. The pending
188.2 JSON working-memory and deterministic-compaction proposal is superseded
by this contract and will not be implemented.

Current implementation starts at 188.4. MEMORY.md is the only canonical durable
memory source.

## Goal

Give each isolated AI Assistant user/workspace one durable MEMORY.md:

    completed runs
      -> every three unprocessed successful runs
      -> model extracts durable facts
      -> merge into today's dated block, at most 100 tokens
      -> later runs read the rolling 30-day window

Memory must stay isolated by user and workspace, remain human-readable, and
avoid replaying the entire file.

## Scope Identity And File Ownership

One logical scope is:

    (user_id, workspace_id)

Requirements:

- user_id comes from trusted host identity; workspace_id comes from a
  server-owned workspace resolver;
- callers cannot submit an arbitrary memory path or select another scope;
- each resolved scope owns exactly one canonical file named MEMORY.md;
- the path resolver must keep the file beneath its configured memory root and
  reject traversal, symlink escape, or scope mismatch;
- all session, run, memory, and usage access must be filtered by the same
  scope;
- the current Hify host adapter may map user_id from RequestContext.actor_id;
  it must add or resolve a stable workspace identity without treating a raw
  client path as authoritative.

## Canonical MEMORY.md Contract

Minimum format:

    # Memory

    ## 2026-07-11
    - Durable fact or preference.

Rules:

- date headings use exactly ## YYYY-MM-DD;
- date headings are unique and ordered oldest to newest;
- dates use the configured workspace timezone;
- all content under one date heading, excluding the heading, totals at most
  100 tokens after each write;
- the same tokenizer or documented deterministic estimator is used for the
  daily cap and tests;
- writes merge, deduplicate, and compress today's full block before enforcing
  the cap; the limit is not per append;
- entries contain durable preferences, decisions, stable facts, and unresolved
  long-lived constraints only;
- secrets, credentials, hidden reasoning, raw logs, transient status, and
  unnecessary personal data are forbidden;
- writes use a per-scope lock plus atomic temp-file replacement; partial or
  interleaved writes are not allowed.

MEMORY.md is the only memory truth source. DB rows may store extraction cursor,
successful-run count, file revision/hash, timestamps, and errors, but never
duplicate memory content.

## Rolling Reader

Default prompt window is 30 calendar days, inclusive of today.

Reader algorithm:

1. Scan structured headings matching ^## YYYY-MM-DD$ with ripgrep, grep, or an
   equivalent bounded line scanner.
2. Find the first valid heading whose date is at least today minus 29 days.
3. Determine its line number and read only from that line through EOF.
4. Parse valid dated blocks from that bounded range; ignore future dates and
   report malformed headings safely.
5. Return empty memory when no valid heading is inside the window.

Fixed tail-N reads and unconditional full-file prompt reads are forbidden.
Scanning headings may inspect line metadata; prompt content reads must start at
the calculated line boundary.

## Extraction Cadence

- only runs ending in COMPLETED count;
- FAILED, CANCELLED, DENIED, interrupted, or duplicate-replay runs do not count;
- the counter is per user/workspace and spans sessions;
- when three unprocessed successful runs exist, process the oldest next batch
  of three exactly once;
- one coordinator pass drains complete batches sequentially; only a final batch
  of one or two remains pending;
- extraction uses a configured model to select durable incremental memory;
- merge output with today's existing block, deduplicate, compress, and enforce
  the full-day 100-token cap;
- advance the durable cursor only after atomic MEMORY.md replacement succeeds;
- each batch has a unique scope/source-run key plus durable input and target
  file hashes; after a crash, matching target hash completes the cursor without
  reapplying memory, while matching input hash safely retries the pending write;
- extraction failure must not change the user run from COMPLETED, must not
  advance the cursor, and must remain retryable and observable;
- fewer than three trailing successful runs remain pending.

A future daily scheduler may flush a trailing batch of one or two runs. That
scheduler is explicitly out of scope here.

## Prompt And Compatibility Boundary

- each new run reads only its own user/workspace rolling MEMORY.md window;
- memory enters the existing working-memory prompt layer; no second compaction
  store is introduced;
- stop writing context_json.aiAssistantMemory as durable memory;
- legacy aiAssistantMemory payloads must not feed canonical prompt memory after
  cutover;
- existing public inspector/API memory fields may remain as read-only
  projections derived from MEMORY.md during compatibility migration;
- removing those public fields requires a separate approved contract.

Existing scheduler, approval, sandbox, durable ToolRunner, event, and response
envelope behavior must remain compatible.

## Out Of Scope

- Spec 189 active customer-assistant spawn bridge;
- dynamic skills or prompt-skill expansion;
- a second JSON/DB memory store;
- vector memory, memory search UI, manual memory editor, or cross-workspace
  memory;
- daily scheduled extraction;
- frontend visual changes.

## Acceptance Criteria

- RED proves cross-user and cross-workspace reads/writes are rejected.
- RED proves reader calculates the rolling start line from structured date
  headings and does not use fixed tail-N reads.
- MEMORY.md survives process/session reload and supplies only the last 30 days
  to a later run.
- Three completed runs across sessions trigger one idempotent extraction;
  non-completed runs do not count.
- Retry after extraction/write failure neither loses nor duplicates a batch.
- Crash recovery is idempotent before replacement, after replacement, and
  before cursor completion.
- Concurrent writers cannot corrupt or exceed today's 100-token block.
- DB inspection proves only operational cursor metadata is stored.
- Legacy JSON memory is no longer written or used as prompt truth; preserved
  public fields, if retained, are derived from MEMORY.md.
- Required tests use MySQL8 for cursor/scope persistence; no SQLite substitute.
- Default deterministic tests use a fake extractor; optional live-model proof
  is separately env-gated and never exposes credentials.
- No customer-assistant or frontend visual files change.
