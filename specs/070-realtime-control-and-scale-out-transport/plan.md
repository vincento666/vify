# Plan 070: Realtime Control And Scale-out Transport

## Decision Gate

Do not start implementation unless at least one is true:

- worker must wait for operator input in the same running connection;
- operator must interrupt in-flight work;
- multiple app instances must fan out events;
- SSE replay/polling has measured product limitations.

## Transport Options

Compare:

- SSE + durable events;
- streaming POST;
- WebSocket;
- Redis/pubsub;
- database polling.

## Source Of Truth

The durable runtime event store remains canonical. WebSocket or pub/sub is only
a delivery channel.

## Transport Hardening

Before implementation, define:

- run/session/tenant authorization;
- at-least-once delivery and idempotent client handling;
- heartbeat and stale connection cleanup;
- reconnect by `runId` and `afterSequence`;
- backpressure and max-connection behavior;
- broker miss recovery from durable event storage.
