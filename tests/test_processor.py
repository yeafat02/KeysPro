"""Tests for parsing, conversion, duplicate handling, and failure safety."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from keyspro.models import ConversionOptions, EventKind, ProcessingEvent  # noqa: E402
from keyspro.processor import ConversionError, TextConversionService  # noqa: E402

SAMPLE_INPUT = "\n\n".join(
    (
        '50047171      "id 214667" '
        'keyval="CC9E89D86A989DA1D6E9160B800E9B7B" checkval="1574E3"',
        '50047172      "id 214668" '
        'keyval="AABBCCDDEEFF00112233445566778899" checkval="89ABCD"',
        '50047173      "id 214669" '
        'keyval="11223344556677889900AABBCCDDEEFF" checkval="123456"',
        '50047172      "id 214670" '
        'keyval="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF" checkval="999999"',
        "INVALID LINE HERE",
    )
) + "\n"

EXPECTED_OUTPUT = "\n".join(
    (
        '"123456","50047171","1",'
        '"CC9E89D86A989DA1D6E9160B800E9B7B","1574E3",""',
        '"123456","50047172","1",'
        '"AABBCCDDEEFF00112233445566778899","89ABCD",""',
        '"123456","50047173","1",'
        '"11223344556677889900AABBCCDDEEFF","123456",""',
        "",
    )
)


class TextConversionServiceTests(unittest.TestCase):
    """Exercise the complete file conversion behavior."""

    def setUp(self) -> None:
        self.service = TextConversionService()

    def test_process_file_matches_expected_output_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.txt"
            input_path.write_text(SAMPLE_INPUT, encoding="utf-8")
            events: list[ProcessingEvent] = []

            summary = self.service.process_file(
                input_path,
                ConversionOptions(mid="123456", index="1"),
                events.append,
            )

            self.assertEqual(EXPECTED_OUTPUT, summary.output_path.read_text(encoding="utf-8"))
            self.assertEqual(5, summary.total_records)
            self.assertEqual(3, summary.converted_records)
            self.assertEqual(1, summary.duplicate_records)
            self.assertEqual(1, summary.invalid_records)
            self.assertEqual(EventKind.COMPLETE, events[-1].kind)
            self.assertTrue(any("Duplicate TID found: 50047172" in e.message for e in events))
            self.assertTrue(any("Invalid record at 5" in e.message for e in events))

    def test_parser_normalizes_lowercase_hex(self) -> None:
        record = self.service.parse_record(
            '7 "id 8" keyval="aabbccddeeff00112233445566778899" checkval="abcdef"'
        )

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual("AABBCCDDEEFF00112233445566778899", record.key_value)
        self.assertEqual("ABCDEF", record.check_value)

    def test_invalid_key_length_is_rejected(self) -> None:
        invalid_key_values = ("A" * 31, "A" * 33)
        for key_value in invalid_key_values:
            with self.subTest(key_length=len(key_value)):
                record = self.service.parse_record(
                    f'7 "id 8" keyval="{key_value}" checkval="ABCDEF"'
                )
                self.assertIsNone(record)

    def test_check_value_must_be_exactly_six_hex_characters(self) -> None:
        invalid_check_values = ("A" * 5, "A" * 7)
        for check_value in invalid_check_values:
            with self.subTest(check_length=len(check_value)):
                record = self.service.parse_record(
                    '7 "id 8" keyval="AABBCCDDEEFF00112233445566778899" '
                    f'checkval="{check_value}"'
                )
                self.assertIsNone(record)

    def test_options_require_valid_mid_and_numeric_index(self) -> None:
        self.service.validate_options(ConversionOptions(mid="ABC123", index="1"))
        with self.assertRaisesRegex(ValueError, "letters and numbers"):
            self.service.validate_options(ConversionOptions(mid="ABC-123", index="1"))
        with self.assertRaisesRegex(ValueError, "Index"):
            self.service.validate_options(ConversionOptions(mid="123456", index=""))

    def test_mid_cannot_exceed_fifteen_characters(self) -> None:
        self.service.validate_options(ConversionOptions(mid="A1" * 7 + "Z", index="1"))
        with self.assertRaisesRegex(ValueError, "15 characters or fewer"):
            self.service.validate_options(ConversionOptions(mid="A1" * 8, index="1"))

    def test_output_path_contains_timestamp_and_avoids_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_path = directory / "keys.txt"
            fixed_time = datetime(2026, 6, 27, 21, 45, 30)
            first_path = self.service.default_output_path(input_path, directory, fixed_time)
            self.assertEqual("keys_converted_20260627_214530.txt", first_path.name)

            first_path.touch()
            second_path = self.service.default_output_path(input_path, directory, fixed_time)
            self.assertEqual("keys_converted_20260627_214530_01.txt", second_path.name)

    def test_input_and_output_cannot_be_the_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.txt"
            input_path.write_text(SAMPLE_INPUT, encoding="utf-8")

            with self.assertRaisesRegex(ConversionError, "cannot overwrite"):
                self.service.process_file(
                    input_path,
                    ConversionOptions(mid="123456", index="1"),
                    lambda _event: None,
                    output_path=input_path,
                )

    def test_empty_file_creates_empty_output_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "empty.txt"
            input_path.write_text("\n\n", encoding="utf-8")
            events: list[ProcessingEvent] = []

            summary = self.service.process_file(
                input_path,
                ConversionOptions(mid="001234", index="01"),
                events.append,
            )

            self.assertEqual("", summary.output_path.read_text(encoding="utf-8"))
            self.assertEqual(0, summary.total_records)
            self.assertEqual(EventKind.COMPLETE, events[-1].kind)
            self.assertEqual(1.0, events[-1].progress)


if __name__ == "__main__":
    unittest.main()
