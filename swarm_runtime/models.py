"""Validated worker requests and immutable result/health records."""
from dataclasses import dataclass
from enum import Enum
import re

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ValidationError(ValueError):
    """Raised when a worker request exceeds the public contract."""


class WorkerState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkerSpec:
    worker_id: str
    task_id: str
    workload_ref: str
    cpu_seconds: int = 10
    memory_mb: int = 256
    wall_time_seconds: int = 60
    output_bytes: int = 65536

    def validate(self) -> None:
        for field_name, value in (("worker_id", self.worker_id), ("task_id", self.task_id)):
            if not isinstance(value, str) or not _ID.fullmatch(value):
                raise ValidationError(f"{field_name} must be a bounded identifier")
        if not isinstance(self.workload_ref, str) or not self.workload_ref.strip() or len(self.workload_ref) > 512:
            raise ValidationError("workload_ref must contain 1..512 characters")
        limits = {
            "cpu_seconds": (self.cpu_seconds, 1, 60),
            "memory_mb": (self.memory_mb, 16, 4096),
            "wall_time_seconds": (self.wall_time_seconds, 1, 300),
            "output_bytes": (self.output_bytes, 0, 1048576),
        }
        for name, (value, lower, upper) in limits.items():
            if not isinstance(value, int) or isinstance(value, bool) or not lower <= value <= upper:
                raise ValidationError(f"{name} must be an integer in [{lower}, {upper}]")


@dataclass(frozen=True)
class WorkerResult:
    exit_code: int
    output_ref: str | None = None

    def validate(self) -> None:
        if not isinstance(self.exit_code, int) or isinstance(self.exit_code, bool):
            raise ValidationError("exit_code must be an integer")
        if self.output_ref is not None and (
            not isinstance(self.output_ref, str) or len(self.output_ref) > 512
        ):
            raise ValidationError("output_ref must be a string of at most 512 characters")


@dataclass(frozen=True)
class HealthReport:
    adapter_healthy: bool
    accepting: bool
    in_flight: int
    capacity: int
