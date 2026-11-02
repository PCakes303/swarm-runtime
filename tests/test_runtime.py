import threading
import time
import unittest

from swarm_runtime import WorkerResult, WorkerRuntime, WorkerSpec, WorkerState


class FakeAdapter:
    def __init__(self, result=None, error=None, healthy=True, gate=None):
        self.result_value = result or WorkerResult(0)
        self.error = error
        self.healthy = healthy
        self.gate = gate

    def run(self, spec):
        if self.gate is not None:
            self.gate.wait(timeout=2)
        if self.error:
            raise self.error
        return self.result_value

    def health(self):
        return self.healthy


def spec(worker="worker.one", task="task.one"):
    return WorkerSpec(worker, task, "artifact://bundle/1")


class RuntimeTests(unittest.TestCase):
    def test_successful_lifecycle_and_audit(self):
        events = []
        runtime = WorkerRuntime(adapter=FakeAdapter(), policy_check=lambda p, s: True, audit_sink=events.append)
        try:
            handle = runtime.submit("principal.one", spec())
            self.assertEqual(handle.result(timeout=2), WorkerResult(0))
            self.assertEqual(handle.state, WorkerState.SUCCEEDED)
            self.assertEqual([e["event"] for e in events], ["worker.admitted", "worker.started", "worker.succeeded"])
        finally:
            runtime.shutdown()

    def test_missing_policy_denies(self):
        runtime = WorkerRuntime(adapter=FakeAdapter(), policy_check=None)
        try:
            with self.assertRaises(PermissionError):
                runtime.submit("principal.one", spec())
        finally:
            runtime.shutdown()

    def test_unhealthy_adapter_denies_admission(self):
        runtime = WorkerRuntime(adapter=FakeAdapter(healthy=False), policy_check=lambda p, s: True)
        try:
            with self.assertRaises(RuntimeError):
                runtime.submit("principal.one", spec())
        finally:
            runtime.shutdown()

    def test_policy_false_denies(self):
        runtime = WorkerRuntime(adapter=FakeAdapter(), policy_check=lambda p, s: False)
        try:
            with self.assertRaises(PermissionError):
                runtime.submit("principal.one", spec())
        finally:
            runtime.shutdown()

    def test_policy_exception_denies(self):
        def broken(p, s):
            raise RuntimeError("policy unavailable")
        runtime = WorkerRuntime(adapter=FakeAdapter(), policy_check=broken)
        try:
            with self.assertRaises(PermissionError):
                runtime.submit("principal.one", spec())
        finally:
            runtime.shutdown()

    def test_audit_admission_failure_denies(self):
        def broken(event):
            raise RuntimeError("audit unavailable")
        runtime = WorkerRuntime(adapter=FakeAdapter(), policy_check=lambda p, s: True, audit_sink=broken)
        try:
            with self.assertRaises(RuntimeError):
                runtime.submit("principal.one", spec())
            self.assertEqual(runtime.health().in_flight, 0)
        finally:
            runtime.shutdown()

    def test_capacity_bounds_queued_and_running_work(self):
        gate = threading.Event()
        runtime = WorkerRuntime(adapter=FakeAdapter(gate=gate), policy_check=lambda p, s: True, max_workers=1, max_queue=0)
        try:
            first = runtime.submit("principal.one", spec())
            deadline = time.time() + 2
            while first.state == WorkerState.PENDING and time.time() < deadline:
                time.sleep(0.005)
            with self.assertRaises(RuntimeError):
                runtime.submit("principal.one", spec("worker.two", "task.two"))
            gate.set()
            first.result(timeout=2)
        finally:
            gate.set()
            runtime.shutdown()

    def test_adapter_failure_marks_worker_failed(self):
        runtime = WorkerRuntime(adapter=FakeAdapter(error=RuntimeError("adapter failed")), policy_check=lambda p, s: True)
        try:
            handle = runtime.submit("principal.one", spec())
            with self.assertRaises(RuntimeError):
                handle.result(timeout=2)
            self.assertEqual(handle.state, WorkerState.FAILED)
        finally:
            runtime.shutdown()

    def test_nonzero_exit_marks_worker_failed(self):
        runtime = WorkerRuntime(adapter=FakeAdapter(result=WorkerResult(7)), policy_check=lambda p, s: True)
        try:
            handle = runtime.submit("principal.one", spec())
            self.assertEqual(handle.result(timeout=2).exit_code, 7)
            self.assertEqual(handle.state, WorkerState.FAILED)
        finally:
            runtime.shutdown()

    def test_health_reports_adapter_state(self):
        runtime = WorkerRuntime(adapter=FakeAdapter(healthy=False), policy_check=lambda p, s: True)
        try:
            report = runtime.health()
            self.assertFalse(report.adapter_healthy)
            self.assertFalse(report.accepting)
        finally:
            runtime.shutdown()


if __name__ == "__main__":
    unittest.main()
