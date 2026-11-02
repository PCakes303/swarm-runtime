# Threat model

## Assets and threats

The supervisor handles workload references, worker/task identifiers, resource requests and lifecycle metadata. Threats include malformed specifications, resource-exhaustion attempts through unbounded submissions, unauthorized work admission, adapter failures and misleading health claims.

## Controls in this scaffold

- Strict bounded worker-spec validation.
- Bounded concurrent plus queued submissions.
- Fail-closed policy callback.
- Lifecycle state tracking and explicit adapter health result.
- Optional audit callback; when configured, callback failures fail closed.
- No workload payload or credential fields in the worker specification.

## Not implemented

There is no process/container/VM sandbox, OS resource-limit enforcement, network namespace, filesystem policy, syscall filtering, secret isolation, cryptographic identity verification, production authorization service, authenticated audit ingestion, durable queue or distributed scheduler. Resource budgets are metadata until an adapter enforces them.

Do not execute untrusted code through an in-process adapter. Do not treat a healthy adapter as proof that a worker or workload is trustworthy. Production use requires a reviewed Sandbox Security adapter and end-to-end policy, identity and audit integration.
