# Agent instructions

Keep runtime and isolation claims precise. Treat worker specifications and workload references as untrusted input. Enforce admission limits and fail closed when policy is absent or unavailable. Never execute a workload in-process as though it were sandboxed. Add tests for every denial, limit and lifecycle transition.
