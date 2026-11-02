# Agent instructions

- Keep runtime and isolation claims precise. This project supervises trusted adapters; it is not a sandbox and does not execute arbitrary workloads itself.
- Treat worker specifications, principal identifiers and workload references as untrusted until validated and authenticated by upstream services.
- Enforce admission limits and fail closed when policy is absent, false, non-boolean or unavailable; only explicit boolean `True` may admit work.
- Keep worker and queue capacity bounded (maximum 256 workers and 4,096 combined slots).
- Require the documented WorkerSpec and WorkerResult contracts; validate every adapter result.
- Treat resource budgets as requested metadata until a reviewed sandbox adapter enforces them at the operating-system boundary.
- Never execute untrusted workloads in-process or claim process/container/VM isolation without evidence.
- Audit callback failures must fail closed; do not silently suppress an admission/audit failure.
- Add tests for every denial, limit, lifecycle transition, concurrency boundary and adapter failure.
- License remains pending review; do not add a license file or infer one.
- Run `python -m unittest discover -s tests -v` before proposing changes.
