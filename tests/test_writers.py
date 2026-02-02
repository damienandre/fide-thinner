"""Tests for writer modules."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from fide_format import COLUMN_NAMES, FIDE_ENCODING
from writers import get_writer
from writers.sqlite_writer import SqliteWriter
from writers.txt_writer import TxtWriter


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "IdNumber": [1001, 1002],
        "Name": ["Player One", "Player Two"],
        "Fed": ["USA", "RUS"],
        "Sex": ["M", "F"],
        "Tit": ["GM", ""],
        "WTit": ["", "WGM"],
        "OTit": ["", ""],
        "FOA": ["", ""],
        "SRtng": [2700, 2400],
        "SGm": [100, 80],
        "SK": [40, 20],
        "RRtng": [2650, 2350],
        "RGm": [50, 40],
        "Rk": [35, 18],
        "BRtng": [2600, 2300],
        "BGm": [30, 20],
        "BK": [30, 15],
        "BDay": ["1990", "1985"],
        "Flag": ["", ""],
    })


@pytest.fixture
def sample_schema():
    """Return a sample CREATE TABLE schema."""
    return """CREATE TABLE fide (
        IdNumber INT PRIMARY KEY,
        Name VARCHAR(60),
        Fed VARCHAR(3),
        Sex VARCHAR(1),
        Tit VARCHAR(3),
        WTit VARCHAR(4),
        OTit VARCHAR(4),
        FOA VARCHAR(3),
        SRtng INT,
        SGm INT,
        SK INT,
        RRtng INT,
        RGm INT,
        Rk INT,
        BRtng INT,
        BGm INT,
        BK INT,
        BDay VARCHAR(4),
        Flag VARCHAR(4)
    )"""


class TestGetWriter:
    """Tests for the get_writer factory function."""

    def test_get_writer_sqlite(self, tmp_path):
        """Test that get_writer returns SqliteWriter for .sqlite files."""
        writer = get_writer(tmp_path / "output.sqlite")
        assert isinstance(writer, SqliteWriter)
        writer.close()

    def test_get_writer_txt(self, tmp_path):
        """Test that get_writer returns TxtWriter for .txt files."""
        writer = get_writer(tmp_path / "output.txt")
        assert isinstance(writer, TxtWriter)
        writer.close()

    def test_get_writer_unsupported_extension(self, tmp_path):
        """Test that get_writer raises ValueError for unsupported extensions."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            get_writer(tmp_path / "output.csv")


class TestSqliteWriter:
    """Tests for SqliteWriter."""

    def test_write_with_schema(self, tmp_path, sample_dataframe, sample_schema):
        """Test writing data with a schema."""
        output_path = tmp_path / "output.sqlite"
        writer = SqliteWriter(output_path)
        writer.write(sample_dataframe, schema=sample_schema)
        writer.close()

        # Verify the data
        conn = sqlite3.connect(output_path)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        assert len(df) == 2
        assert df.loc[0, "IdNumber"] == 1001
        assert df.loc[0, "Name"] == "Player One"

    def test_write_multiple_chunks(self, tmp_path, sample_dataframe, sample_schema):
        """Test writing multiple DataFrames (chunks)."""
        output_path = tmp_path / "output.sqlite"
        writer = SqliteWriter(output_path)

        # Write first chunk with schema
        writer.write(sample_dataframe.iloc[:1], schema=sample_schema)
        # Write second chunk without schema
        writer.write(sample_dataframe.iloc[1:])
        writer.close()

        # Verify the data
        conn = sqlite3.connect(output_path)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        assert len(df) == 2

    def test_removes_existing_file(self, tmp_path, sample_dataframe, sample_schema):
        """Test that existing file is removed before writing."""
        output_path = tmp_path / "output.sqlite"

        # Create a dummy file
        output_path.write_text("dummy content")
        assert output_path.exists()

        writer = SqliteWriter(output_path)
        writer.write(sample_dataframe, schema=sample_schema)
        writer.close()

        # Verify it's a valid SQLite database now
        conn = sqlite3.connect(output_path)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        assert len(df) == 2


class TestTxtWriter:
    """Tests for TxtWriter."""

    def test_write_basic(self, tmp_path, sample_dataframe):
        """Test basic writing to text file."""
        output_path = tmp_path / "output.txt"
        writer = TxtWriter(output_path)
        writer.write(sample_dataframe)
        writer.close()

        # Verify the file exists and has content
        assert output_path.exists()
        with open(output_path, "r", encoding=FIDE_ENCODING) as f:
            lines = f.readlines()

        # Header + 2 data lines
        assert len(lines) == 3

    def test_write_header_format(self, tmp_path, sample_dataframe):
        """Test that header line is properly formatted."""
        output_path = tmp_path / "output.txt"
        writer = TxtWriter(output_path)
        writer.write(sample_dataframe)
        writer.close()

        with open(output_path, "r", encoding=FIDE_ENCODING) as f:
            header = f.readline()

        assert "ID Number" in header
        assert "Name" in header
        assert "Fed" in header

    def test_write_data_format(self, tmp_path, sample_dataframe):
        """Test that data lines are properly formatted with fixed widths."""
        output_path = tmp_path / "output.txt"
        writer = TxtWriter(output_path)
        writer.write(sample_dataframe)
        writer.close()

        with open(output_path, "r", encoding=FIDE_ENCODING) as f:
            lines = f.readlines()

        # Check first data line (after header)
        data_line = lines[1]

        # IdNumber should be at position 0-15
        id_num = data_line[0:15].strip()
        assert id_num == "1001"

        # Name should be at position 15-75
        name = data_line[15:75].strip()
        assert name == "Player One"

    def test_write_multiple_chunks(self, tmp_path, sample_dataframe):
        """Test writing multiple DataFrames (chunks)."""
        output_path = tmp_path / "output.txt"
        writer = TxtWriter(output_path)

        # Write first chunk
        writer.write(sample_dataframe.iloc[:1])
        # Write second chunk
        writer.write(sample_dataframe.iloc[1:])
        writer.close()

        with open(output_path, "r", encoding=FIDE_ENCODING) as f:
            lines = f.readlines()

        # Header + 2 data lines (header only written once)
        assert len(lines) == 3

    def test_write_empty_dataframe(self, tmp_path):
        """Test writing empty DataFrame."""
        output_path = tmp_path / "output.txt"
        writer = TxtWriter(output_path)
        writer.write(pd.DataFrame())
        writer.close()

        # File may or may not exist, but should not error
        # If it exists, it should be empty or just header
