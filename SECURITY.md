# Security

This repository is an experimental worker supervisor, not a security sandbox. It does not execute untrusted code, isolate processes, restrict network or filesystem access, or enforce operating-system CPU/memory quotas. Resource values are admission metadata passed to a trusted adapter. The adapter must enforce them in an independently reviewed sandbox before handling untrusted workloads.

Policy and audit callbacks are integration seams, not production identity, authorization or provenance services. Missing policy denies work. Never treat worker health as proof of trust.
