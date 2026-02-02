"""Tests for fide_format module."""

import pytest

from fide_format import (
    COLUMN_MAP,
    COLUMN_NAMES,
    FIDE_COLUMNS,
    INTEGER_COLUMNS,
    MIN_LINE_LENGTH,
    ColumnSpec,
)


class TestColumnSpec:
    """Tests for ColumnSpec dataclass."""

    def test_column_spec_end_property(self):
        """Test that end property calculates correctly."""
        col = ColumnSpec("Test", 10, 5)
        assert col.end == 15

    def test_column_spec_frozen(self):
        """Test that ColumnSpec is immutable."""
        col = ColumnSpec("Test", 0, 10)
        with pytest.raises(AttributeError):
            col.name = "Changed"


class TestFideColumns:
    """Tests for FIDE column specifications."""

    def test_columns_are_contiguous(self):
        """Test that columns are defined contiguously without gaps."""
        for i in range(len(FIDE_COLUMNS) - 1):
            current = FIDE_COLUMNS[i]
            next_col = FIDE_COLUMNS[i + 1]
            assert current.end == next_col.start, (
                f"Gap between {current.name} (end={current.end}) and "
                f"{next_col.name} (start={next_col.start})"
            )

    def test_first_column_starts_at_zero(self):
        """Test that the first column starts at position 0."""
        assert FIDE_COLUMNS[0].start == 0

    def test_id_number_is_first_column(self):
        """Test that IdNumber is the first column."""
        assert FIDE_COLUMNS[0].name == "IdNumber"

    def test_column_map_contains_all_columns(self):
        """Test that COLUMN_MAP contains all columns."""
        assert len(COLUMN_MAP) == len(FIDE_COLUMNS)
        for col in FIDE_COLUMNS:
            assert col.name in COLUMN_MAP
            assert COLUMN_MAP[col.name] == col

    def test_column_names_order_matches(self):
        """Test that COLUMN_NAMES matches FIDE_COLUMNS order."""
        expected = [col.name for col in FIDE_COLUMNS]
        assert COLUMN_NAMES == expected

    def test_min_line_length(self):
        """Test MIN_LINE_LENGTH is correct."""
        last_col = FIDE_COLUMNS[-1]
        assert MIN_LINE_LENGTH == last_col.end

    def test_integer_columns_are_valid(self):
        """Test that all integer columns exist in FIDE_COLUMNS."""
        column_names = {col.name for col in FIDE_COLUMNS}
        for int_col in INTEGER_COLUMNS:
            assert int_col in column_names, f"{int_col} not in FIDE_COLUMNS"

    def test_id_number_is_integer(self):
        """Test that IdNumber is marked as an integer column."""
        assert "IdNumber" in INTEGER_COLUMNS

    def test_expected_columns_exist(self):
        """Test that all expected columns are defined."""
        expected = {
            "IdNumber", "Name", "Fed", "Sex", "Tit", "WTit", "OTit",
            "FOA", "SRtng", "SGm", "SK", "RRtng", "RGm", "Rk",
            "BRtng", "BGm", "BK", "BDay", "Flag"
        }
        actual = set(COLUMN_NAMES)
        assert actual == expected
