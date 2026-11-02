# Worker contract v1

## Purpose

The runtime is a bounded supervisor around an injected execution adapter. It validates a worker request, obtains an explicit policy decision, reserves bounded capacity, records lifecycle events, delegates to the adapter and reports health.

## Worker specification

A request contains:
- `worker_id`: stable bounded worker identity.
- `task_id`: stable bounded task reference.
- `workload_ref`: opaque artifact or workload reference; payload bytes and credentials are not embedded.
- `cpu_seconds`: requested budget, 1–60.
- `memory_mb`: requested budget, 16–4096.
- `wall_time_seconds`: requested wall-clock budget, 1–300.
- `output_bytes`: requested output budget, 0–1,048,576.

These are requested budgets, not enforced operating-system limits. The trusted adapter must enforce them.

## Admission and lifecycle

Admission requires a policy callback returning exactly `True`. Missing callbacks, false decisions and callback exceptions deny submission. Active plus queued submissions are bounded by `max_workers + max_queue`; `max_workers` is capped at 256, `max_queue` at 4,096, and combined capacity at 4,096. Policy admission accepts only explicit boolean `True`.

Lifecycle states are `pending`, `running`, `succeeded` and `failed`. Adapter exceptions and nonzero exit codes fail the worker. Completion events are emitted through the optional audit callback. If an audit callback is configured and fails, the submission or completion is treated as failed.

## Adapter contract

An adapter implements `run(spec) -> WorkerResult` and `health() -> bool`. It is responsible for execution isolation and enforcement before processing untrusted workloads. The included tests use an in-process fake adapter only; it is not an execution implementation.

## Trust boundary

Identity, policy, audit and sandbox integrations are explicit callbacks/contracts. This scaffold does not authenticate principals, issue identities, enforce production policy, authenticate audit producers, isolate processes, block network access or constrain filesystem access.
