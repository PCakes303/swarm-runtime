"""Bounded concurrent worker supervisor with fail-closed admission."""
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import threading
from typing import Callable, Protocol

from .models import HealthReport, WorkerResult, WorkerSpec, WorkerState


class WorkerAdapter(Protocol):
    def run(self, spec: WorkerSpec) -> WorkerResult: ...
    def health(self) -> bool: ...


PolicyCheck = Callable[[str, WorkerSpec], bool]
AuditSink = Callable[[dict], None]


class WorkerHandle:
    def __init__(self, spec: WorkerSpec):
        self.worker_id = spec.worker_id
        self.task_id = spec.task_id
        self._state = WorkerState.PENDING
        self._lock = threading.RLock()
        self._future: Future | None = None
        self.error: str | None = None
        self.started_at: str | None = None
        self.completed_at: str | None = None

    @property
    def state(self) -> WorkerState:
        with self._lock:
            return self._state

    def _attach(self, future: Future) -> None:
        with self._lock:
            self._future = future

    def _running(self) -> None:
        with self._lock:
            self._state = WorkerState.RUNNING
            self.started_at = datetime.now(timezone.utc).isoformat()

    def _finish(self, state: WorkerState, error: str | None = None) -> None:
        with self._lock:
            self._state = state
            self.error = error
            self.completed_at = datetime.now(timezone.utc).isoformat()

    def result(self, timeout: float | None = None) -> WorkerResult:
        with self._lock:
            future = self._future
        if future is None:
            raise RuntimeError("worker submission has not been attached")
        return future.result(timeout=timeout)


class WorkerRuntime:
    """Supervisor only: an injected adapter owns execution and isolation."""

    def __init__(
        self,
        *,
        adapter: WorkerAdapter,
        policy_check: PolicyCheck | None,
        audit_sink: AuditSink | None = None,
        max_workers: int = 4,
        max_queue: int = 16,
    ):
        if not isinstance(max_workers, int) or isinstance(max_workers, bool) or not 1 <= max_workers <= 256:
            raise ValueError("max_workers must be an integer in [1, 256]")
        if not isinstance(max_queue, int) or isinstance(max_queue, bool) or not 0 <= max_queue <= 4096:
            raise ValueError("max_queue must be an integer in [0, 4096]")
        if max_workers + max_queue > 4096:
            raise ValueError("combined worker and queue capacity must not exceed 4096")
        if not callable(getattr(adapter, "run", None)) or not callable(getattr(adapter, "health", None)):
            raise TypeError("adapter must implement run(spec) and health()")
        self.adapter = adapter
        self.policy_check = policy_check
        self.audit_sink = audit_sink
        self.max_workers = max_workers
        self.max_queue = max_queue
        self.capacity = max_workers + max_queue
        self._slots = threading.BoundedSemaphore(self.capacity)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="swarm-worker")
        self._lock = threading.RLock()
        self._in_flight = 0
        self._closed = False

    def _emit(self, event: str, spec: WorkerSpec, state: str) -> None:
        if self.audit_sink is not None:
            self.audit_sink({
                "event": event,
                "worker_id": spec.worker_id,
                "task_id": spec.task_id,
                "state": state,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            })

    def submit(self, principal_id: str, spec: WorkerSpec) -> WorkerHandle:
        if not isinstance(spec, WorkerSpec):
            raise TypeError("spec must be a WorkerSpec")
        spec.validate()
        if not isinstance(principal_id, str) or not principal_id.strip() or len(principal_id) > 128:
            raise PermissionError("a trusted principal identifier is required")
        if not self.health().adapter_healthy:
            raise RuntimeError("worker adapter is unhealthy; admission denied")
        if self.policy_check is None:
            raise PermissionError("policy unavailable; worker admission denied")
        try:
            allowed = self.policy_check(principal_id, spec)
        except Exception as exc:
            raise PermissionError("policy evaluation failed; worker admission denied") from exc
        if allowed is not True:
            raise PermissionError("policy denied worker admission")

        with self._lock:
            if self._closed:
                raise RuntimeError("worker runtime is shut down")
            if not self._slots.acquire(blocking=False):
                raise RuntimeError("worker capacity reached")
            self._in_flight += 1

        try:
            self._emit("worker.admitted", spec, WorkerState.PENDING.value)
            handle = WorkerHandle(spec)
            future = self._executor.submit(self._run, handle, spec)
            handle._attach(future)
            future.add_done_callback(lambda _: self._release_slot())
            return handle
        except Exception:
            self._release_slot()
            raise

    def _release_slot(self) -> None:
        with self._lock:
            self._in_flight -= 1
            self._slots.release()

    def _run(self, handle: WorkerHandle, spec: WorkerSpec) -> WorkerResult:
        handle._running()
        try:
            self._emit("worker.started", spec, WorkerState.RUNNING.value)
            result = self.adapter.run(spec)
            if not isinstance(result, WorkerResult):
                raise TypeError("adapter must return WorkerResult")
            result.validate()
            if result.exit_code == 0:
                self._emit("worker.succeeded", spec, WorkerState.SUCCEEDED.value)
                handle._finish(WorkerState.SUCCEEDED)
            else:
                self._emit("worker.failed", spec, WorkerState.FAILED.value)
                handle._finish(WorkerState.FAILED, f"adapter exit code {result.exit_code}")
            return result
        except Exception as exc:
            handle._finish(WorkerState.FAILED, type(exc).__name__)
            try:
                self._emit("worker.failed", spec, WorkerState.FAILED.value)
            except Exception:
                pass
            raise

    def health(self) -> HealthReport:
        try:
            adapter_healthy = self.adapter.health() is True
        except Exception:
            adapter_healthy = False
        with self._lock:
            return HealthReport(
                adapter_healthy=adapter_healthy,
                accepting=not self._closed and adapter_healthy,
                in_flight=self._in_flight,
                capacity=self.capacity,
            )

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)
