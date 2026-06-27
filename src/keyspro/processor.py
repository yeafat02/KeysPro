"""Text parsing and conversion service with atomic output writing."""

from __future__ import annotations

import csv
import logging
import os
import re
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from keyspro.models import (
    ConversionOptions,
    ConversionSummary,
    EventKind,
    KeyRecord,
    ProcessingEvent,
)

ProgressCallback = Callable[[ProcessingEvent], None]

_RECORD_PATTERN = re.compile(
    r'^\s*(?P<tid>\d+)\s+"id\s+(?P<source_id>\d+)"\s+'
    r'keyval="(?P<key_value>[0-9A-Fa-f]{32})"\s+'
    r'checkval="(?P<check_value>[0-9A-Fa-f]{6})"\s*$'
)


class ConversionError(RuntimeError):
    """Raised when a conversion cannot be started or completed safely."""


class TextConversionService:
    """Convert structured source records into KeysPro output rows."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("keyspro.processor")

    @staticmethod
    def validate_options(options: ConversionOptions) -> None:
        """Validate MID and Index without converting away leading zeroes."""

        if not options.mid or not options.mid.isascii() or not options.mid.isalnum():
            raise ValueError("MID must contain English letters and numbers only.")
        if len(options.mid) > 15:
            raise ValueError("MID must be 15 characters or fewer.")
        if not options.index or not options.index.isdecimal():
            raise ValueError("Index must contain numbers only.")

    @staticmethod
    def parse_record(line: str) -> KeyRecord | None:
        """Parse a source record, returning ``None`` for an invalid line."""

        match = _RECORD_PATTERN.fullmatch(line)
        if match is None:
            return None
        return KeyRecord(
            tid=match.group("tid"),
            key_value=match.group("key_value").upper(),
            check_value=match.group("check_value").upper(),
        )

    @staticmethod
    def default_output_path(
        input_path: Path,
        output_directory: Path | None = None,
        timestamp: datetime | None = None,
    ) -> Path:
        """Create a timestamped, non-conflicting output path."""

        target_directory = output_directory or input_path.parent
        date_time = timestamp or datetime.now()
        base_name = f"{input_path.stem}_converted_{date_time:%Y%m%d_%H%M%S}"
        candidate = target_directory / f"{base_name}.txt"
        counter = 1
        while candidate.exists():
            candidate = target_directory / f"{base_name}_{counter:02d}.txt"
            counter += 1
        return candidate

    @staticmethod
    def _count_records(input_path: Path) -> int:
        with input_path.open("r", encoding="utf-8-sig", newline=None) as source:
            return sum(1 for line in source if line.strip())

    @staticmethod
    def _format_output_line(options: ConversionOptions, record: KeyRecord) -> str:
        fields = [
            options.mid,
            record.tid,
            options.index,
            record.key_value,
            record.check_value,
            "",
        ]
        return ",".join(f'"{value}"' for value in fields)

    def process_file(
        self,
        input_path: Path,
        options: ConversionOptions,
        callback: ProgressCallback,
        output_path: Path | None = None,
    ) -> ConversionSummary:
        """Convert a UTF-8 text file and atomically replace its output file."""

        self.validate_options(options)
        resolved_input = input_path.expanduser().resolve()
        if not resolved_input.is_file():
            raise ConversionError("The selected input file does not exist.")
        if resolved_input.suffix.lower() != ".txt":
            raise ConversionError("Please select a .txt input file.")

        resolved_output = (output_path or self.default_output_path(resolved_input)).resolve()
        if resolved_output == resolved_input:
            raise ConversionError("The output file cannot overwrite the input file.")

        try:
            total_records = self._count_records(resolved_input)
        except UnicodeDecodeError as exc:
            raise ConversionError("The input file must use UTF-8 text encoding.") from exc
        except OSError as exc:
            raise ConversionError(f"Could not read the input file: {exc}") from exc

        callback(ProcessingEvent(EventKind.STATUS, "Loading file...", 0, total_records))
        seen_tids: set[str] = set()
        converted = 0
        duplicates = 0
        invalid = 0
        logical_record = 0
        temporary_path: Path | None = None

        try:
            resolved_output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=f".{resolved_output.stem}_",
                suffix=".tmp",
                dir=resolved_output.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer = csv.writer(
                    temporary_file,
                    quoting=csv.QUOTE_ALL,
                    lineterminator="\n",
                )

                with resolved_input.open("r", encoding="utf-8-sig", newline=None) as source:
                    for physical_line, raw_line in enumerate(source, start=1):
                        stripped_line = raw_line.strip()
                        if not stripped_line:
                            continue

                        logical_record += 1
                        callback(
                            ProcessingEvent(
                                EventKind.STATUS,
                                f"Reading record {logical_record}...",
                                logical_record - 1,
                                total_records,
                            )
                        )
                        record = self.parse_record(stripped_line)
                        if record is None:
                            invalid += 1
                            callback(
                                ProcessingEvent(
                                    EventKind.INVALID,
                                    f"Invalid record at {logical_record} "
                                    f"(file line {physical_line}); skipping...",
                                    logical_record,
                                    total_records,
                                )
                            )
                            continue

                        if record.tid in seen_tids:
                            duplicates += 1
                            callback(
                                ProcessingEvent(
                                    EventKind.DUPLICATE,
                                    f"Duplicate TID found: {record.tid}; skipping duplicate...",
                                    logical_record,
                                    total_records,
                                )
                            )
                            continue

                        seen_tids.add(record.tid)
                        output_fields = [
                            options.mid,
                            record.tid,
                            options.index,
                            record.key_value,
                            record.check_value,
                            "",
                        ]
                        writer.writerow(output_fields)
                        converted += 1
                        callback(
                            ProcessingEvent(
                                EventKind.CONVERTED,
                                f"Converted TID: {record.tid}",
                                logical_record,
                                total_records,
                                output_line=self._format_output_line(options, record),
                            )
                        )

            os.replace(temporary_path, resolved_output)
            temporary_path = None
        except UnicodeDecodeError as exc:
            raise ConversionError("The input file must use UTF-8 text encoding.") from exc
        except OSError as exc:
            raise ConversionError(f"Could not create the output file: {exc}") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    self._logger.exception("Could not remove temporary file %s", temporary_path)

        summary = ConversionSummary(
            total_records=total_records,
            converted_records=converted,
            duplicate_records=duplicates,
            invalid_records=invalid,
            output_path=resolved_output,
        )
        callback(
            ProcessingEvent(
                EventKind.COMPLETE,
                "Conversion completed.",
                total_records,
                total_records,
                summary=summary,
            )
        )
        self._logger.info(
            "Conversion completed: input=%s output=%s total=%d "
            "converted=%d duplicates=%d invalid=%d",
            resolved_input,
            resolved_output,
            total_records,
            converted,
            duplicates,
            invalid,
        )
        return summary
