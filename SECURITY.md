# Security Policy

This repository is an experimental worker supervisor, not a security sandbox. It does not execute untrusted code itself, isolate processes, restrict network/filesystem access, or enforce operating-system CPU/memory quotas. Resource values are admission metadata until an independently reviewed adapter enforces them.

## Reporting

Do not publish exploitable vulnerabilities, credentials, private keys, or sensitive operational data in public issues. Use GitHub private vulnerability reporting or a private security advisory if enabled for this repository. A dedicated private reporting address is not published here; if private reporting is unavailable, the owner must configure an owner-approved private channel before production use.

## Trust and execution boundaries

- Policy and audit callbacks are integration seams, not production identity, authorization or provenance services.
- Only explicit boolean `True` admits a worker or reports adapter health as healthy.
- Supervisor capacity is bounded to at most 256 workers and 4,096 combined worker/queue slots.
- Never use an in-process adapter for untrusted workloads. Production execution requires a reviewed OS-level sandbox backend with resource, filesystem, network, secret and tenant isolation.
- A healthy adapter is not proof that a worker or workload is trustworthy.
