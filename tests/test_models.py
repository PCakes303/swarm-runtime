import unittest
from swarm_runtime import ValidationError, WorkerSpec


class WorkerSpecTests(unittest.TestCase):
    def test_valid_spec(self):
        WorkerSpec("worker.one", "task.one", "artifact://bundle/1").validate()

    def test_identifier_rejected(self):
        with self.assertRaises(ValidationError):
            WorkerSpec("bad id", "task.one", "artifact://bundle/1").validate()

    def test_resource_limits_are_bounded(self):
        with self.assertRaises(ValidationError):
            WorkerSpec("worker.one", "task.one", "artifact://bundle/1", memory_mb=8192).validate()

    def test_boolean_is_not_an_integer_budget(self):
        with self.assertRaises(ValidationError):
            WorkerSpec("worker.one", "task.one", "artifact://bundle/1", cpu_seconds=True).validate()

    def test_workload_reference_required(self):
        with self.assertRaises(ValidationError):
            WorkerSpec("worker.one", "task.one", " ").validate()


if __name__ == "__main__":
    unittest.main()
