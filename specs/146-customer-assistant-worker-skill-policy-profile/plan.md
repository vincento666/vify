# Plan

## Status

Complete.

## Slice 146.1 Worker Skill Policy Refs

1. RED backend tests for profile parsing/API persistence/React evidence.
2. RED frontend tests for profile contract and visible/editable fields.
3. Add profile fields to domain model, schema, repository, API schemas, and
   React registry/evidence.
4. Add MySQL-compatible migration and local compatibility column guard.
5. Render/edit the refs in the operator workbench.
6. Run focused backend/frontend, MySQL schema, rem/full frontend, build, and
   browser UAT gates.

## Result

Slice 146.1 is complete. Worker profiles now carry tool policy and output
schema refs from defaults/env JSON through persisted MySQL overrides, API
payloads, ReAct worker evidence, task/profile UI, and browser UAT.
