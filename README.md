# Swarm Runtime

Experimental bounded worker supervisor and adapter contract for the hybrid agent swarm.

## What this scaffold does

- Validates worker/task identifiers, opaque workload references and bounded resource requests.
- Requires an explicit policy callback returning exactly `True`; missing, false or raising policy callbacks deny admission.
- Bounds concurrent plus queued submissions.
- Tracks pending, running, succeeded and failed lifecycle states.
- Emits optional lifecycle events through an audit callback. If configured, audit failures fail closed.
- Reports adapter health and supervisor capacity.

## Quick start

The runtime requires an injected adapter. The example below is a test-style adapter, not an isolation implementation:

```python
from swarm_runtime import WorkerResult, WorkerRuntime, WorkerSpec

class DemoAdapter:
    def run(self, spec):
        return WorkerResult(exit_code=0)
    def health(self):
        return True

runtime = WorkerRuntime(
    adapter=DemoAdapter(),
    policy_check=lambda principal_id, spec: principal_id == "principal.demo",
    max_workers=2,
    max_queue=4,
)
try:
    handle = runtime.submit(
        "principal.demo",
        WorkerSpec("worker.demo", "task.demo", "artifact://bundle/123"),
    )
    print(handle.result(timeout=5))
finally:
    runtime.shutdown()
```

## Security boundary

**This is not a sandbox.** The runtime does not execute workloads itself and does not isolate processes, containers or virtual machines. It does not enforce operating-system CPU/memory limits or network/filesystem restrictions. Resource budgets are validated admission metadata until a trusted adapter enforces them.

Do not use an in-process adapter for untrusted workloads. Production execution requires a reviewed adapter from the planned Sandbox Security component, plus real Identity & Trust, Policy Engine and Audit & Provenance integrations.

See [worker contract](docs/WORKER-CONTRACT.md) and [threat model](docs/THREAT-MODEL.md). Python 3.10–3.12 are covered by CI. No release is published; repository-specific license selection is pending review.
