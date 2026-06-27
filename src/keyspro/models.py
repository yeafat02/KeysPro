"""Domain models used by the text conversion service and user interface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ConversionOptions:
    """User-provided values applied to every converted record."""

    mid: str
    index: str


@dataclass(frozen=True, slots=True)
class KeyRecord:
    """A valid record parsed from one source line."""

    tid: str
    key_value: str
    check_value: str


@dataclass(frozen=True, slots=True)
class ConversionSummary:
    """Final counters and output location for a completed conversion."""

    total_records: int
    converted_records: int
    duplicate_records: int
    invalid_records: int
    output_path: Path


class EventKind(StrEnum):
    """Kinds of progress events emitted during conversion."""

    STATUS = "status"
    CONVERTED = "converted"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class ProcessingEvent:
    """A thread-safe progress update sent to the UI."""

    kind: EventKind
    message: str
    processed_records: int
    total_records: int
    output_line: str | None = None
    summary: ConversionSummary | None = None

    @property
    def progress(self) -> float:
        """Return normalized progress in the inclusive range 0.0 to 1.0."""

        if self.total_records == 0:
            return 1.0 if self.kind is EventKind.COMPLETE else 0.0
        return min(1.0, max(0.0, self.processed_records / self.total_records))

