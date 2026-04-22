"""Tests for reader modules."""

import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from fide_format import COLUMN_NAMES, FIDE_COLUMNS, FIDE_ENCODING, REVERSE_XML_TAG_MAP
from readers import get_reader
from readers.sqlite_reader import SqliteReader
from readers.txt_reader import TxtReader
from readers.xml_reader import XmlReader


@pytest.fixture
def sample_sqlite_db(tmp_path):
    """Create a sample SQLite database for testing."""
    db_path = tmp_path / "test_fide.sqlite"
    conn = sqlite3.connect(db_path)

    # Create table with minimal schema
    conn.execute("""
        CREATE TABLE fide (
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
        )
    """)

    # Insert test data
    test_data = [
        (1001, "Player One", "USA", "M", "GM", "", "", "", 2700, 100, 40, 2650, 50, 35, 2600, 30, 30, "1990", ""),
        (1002, "Player Two", "RUS", "F", "", "WGM", "", "", 2400, 80, 20, 2350, 40, 18, 2300, 20, 15, "1985", ""),
        (1003, "Player Three", "GER", "M", "", "", "IA", "", 2200, 50, 15, 2150, 25, 12, 2100, 15, 10, "2000", "i"),
        (1004, "Player Four", "FRA", "M", "", "", "", "", 1800, 20, 10, 1750, 10, 8, 1700, 5, 5, "2005", ""),
    ]

    conn.executemany(
        "INSERT INTO fide VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        test_data
    )
    conn.commit()
    conn.close()

    return db_path


def _format_fide_line(data: dict) -> str:
    """Format a row as a fixed-width FIDE line using column specs."""
    line_length = FIDE_COLUMNS[-1].end
    line = [" "] * line_length
    for col in FIDE_COLUMNS:
        value = str(data.get(col.name, ""))
        # Left-align the value within the column width
        for i, char in enumerate(value[:col.width]):
            line[col.start + i] = char
    return "".join(line)


@pytest.fixture
def sample_txt_file(tmp_path):
    """Create a sample fixed-width text file for testing."""
    txt_path = tmp_path / "test_fide.txt"

    # Test data as dictionaries
    test_rows = [
        {"IdNumber": 1001, "Name": "Player One", "Fed": "USA", "Sex": "M", "Tit": "GM", "WTit": "", "OTit": "", "FOA": "", "SRtng": 2700, "SGm": 100, "SK": 40, "RRtng": 2650, "RGm": 50, "Rk": 35, "BRtng": 2600, "BGm": 30, "BK": 30, "BDay": "1990", "Flag": ""},
        {"IdNumber": 1002, "Name": "Player Two", "Fed": "RUS", "Sex": "F", "Tit": "", "WTit": "WGM", "OTit": "", "FOA": "", "SRtng": 2400, "SGm": 80, "SK": 20, "RRtng": 2350, "RGm": 40, "Rk": 18, "BRtng": 2300, "BGm": 20, "BK": 15, "BDay": "1985", "Flag": ""},
        {"IdNumber": 1003, "Name": "Player Three", "Fed": "GER", "Sex": "M", "Tit": "", "WTit": "", "OTit": "IA", "FOA": "", "SRtng": 2200, "SGm": 50, "SK": 15, "RRtng": 2150, "RGm": 25, "Rk": 12, "BRtng": 2100, "BGm": 15, "BK": 10, "BDay": "2000", "Flag": "i"},
        {"IdNumber": 1004, "Name": "Player Four", "Fed": "FRA", "Sex": "M", "Tit": "", "WTit": "", "OTit": "", "FOA": "", "SRtng": 1800, "SGm": 20, "SK": 10, "RRtng": 1750, "RGm": 10, "Rk": 8, "BRtng": 1700, "BGm": 5, "BK": 5, "BDay": "2005", "Flag": ""},
    ]

    with open(txt_path, "w", encoding=FIDE_ENCODING) as f:
        # Write header line
        header_data = {"IdNumber": "ID Number", "Name": "Name", "Fed": "Fed", "Sex": "Sex", "Tit": "Tit", "WTit": "WTit", "OTit": "OTit", "FOA": "FOA", "SRtng": "SRtng", "SGm": "SGm", "SK": "SK", "RRtng": "RRtng", "RGm": "RGm", "Rk": "Rk", "BRtng": "BRtng", "BGm": "BGm", "BK": "BK", "BDay": "BDay", "Flag": "Flag"}
        f.write(_format_fide_line(header_data) + "\n")
        # Write data lines
        for row in test_rows:
            f.write(_format_fide_line(row) + "\n")

    return txt_path


def _build_player_xml(data: dict) -> str:
    """Build a <player> XML element string from a data dictionary."""
    parts = ["<player>"]
    for col_name in COLUMN_NAMES:
        xml_tag = REVERSE_XML_TAG_MAP.get(col_name)
        if xml_tag is None:
            continue
        value = str(data.get(col_name, ""))
        parts.append(f"<{xml_tag}>{value}</{xml_tag}>")
    parts.append("</player>")
    return "".join(parts)


@pytest.fixture
def sample_xml_file(tmp_path):
    """Create a sample XML file for testing."""
    xml_path = tmp_path / "test_fide.xml"

    test_rows = [
        {"IdNumber": 1001, "Name": "Player One", "Fed": "USA", "Sex": "M", "Tit": "GM", "WTit": "", "OTit": "", "FOA": "", "SRtng": 2700, "SGm": 100, "SK": 40, "RRtng": 2650, "RGm": 50, "Rk": 35, "BRtng": 2600, "BGm": 30, "BK": 30, "BDay": "1990", "Flag": ""},
        {"IdNumber": 1002, "Name": "Player Two", "Fed": "RUS", "Sex": "F", "Tit": "", "WTit": "WGM", "OTit": "", "FOA": "", "SRtng": 2400, "SGm": 80, "SK": 20, "RRtng": 2350, "RGm": 40, "Rk": 18, "BRtng": 2300, "BGm": 20, "BK": 15, "BDay": "1985", "Flag": ""},
        {"IdNumber": 1003, "Name": "Player Three", "Fed": "GER", "Sex": "M", "Tit": "", "WTit": "", "OTit": "IA", "FOA": "", "SRtng": 2200, "SGm": 50, "SK": 15, "RRtng": 2150, "RGm": 25, "Rk": 12, "BRtng": 2100, "BGm": 15, "BK": 10, "BDay": "2000", "Flag": "i"},
        {"IdNumber": 1004, "Name": "Player Four", "Fed": "FRA", "Sex": "M", "Tit": "", "WTit": "", "OTit": "", "FOA": "", "SRtng": 1800, "SGm": 20, "SK": 10, "RRtng": 1750, "RGm": 10, "Rk": 8, "BRtng": 1700, "BGm": 5, "BK": 5, "BDay": "2005", "Flag": ""},
    ]

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write("<playerslist>\n")
        for row in test_rows:
            f.write(_build_player_xml(row) + "\n")
        f.write("</playerslist>\n")

    return xml_path


class TestGetReader:
    """Tests for the get_reader factory function."""

    def test_get_reader_sqlite(self, sample_sqlite_db):
        """Test that get_reader returns SqliteReader for .sqlite files."""
        reader = get_reader(sample_sqlite_db)
        assert isinstance(reader, SqliteReader)
        reader.close()

    def test_get_reader_txt(self, sample_txt_file):
        """Test that get_reader returns TxtReader for .txt files."""
        reader = get_reader(sample_txt_file)
        assert isinstance(reader, TxtReader)
        reader.close()

    def test_get_reader_xml(self, sample_xml_file):
        """Test that get_reader returns XmlReader for .xml files."""
        reader = get_reader(sample_xml_file)
        assert isinstance(reader, XmlReader)
        reader.close()

    def test_get_reader_unsupported_extension(self, tmp_path):
        """Test that get_reader raises ValueError for unsupported extensions."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            get_reader(tmp_path / "test.csv")


class TestSqliteReader:
    """Tests for SqliteReader."""

    def test_read_columns(self, sample_sqlite_db):
        """Test reading specific columns."""
        reader = SqliteReader(sample_sqlite_db)
        df = reader.read_columns(["IdNumber", "Tit", "WTit", "OTit"])
        reader.close()

        assert len(df) == 4
        assert list(df.columns) == ["IdNumber", "Tit", "WTit", "OTit"]

        # Check specific values
        gm_player = df[df["IdNumber"] == 1001].iloc[0]
        assert gm_player["Tit"] == "GM"

    def test_read_all(self, sample_sqlite_db):
        """Test reading all data."""
        reader = SqliteReader(sample_sqlite_db)
        df = reader.read_all()
        reader.close()

        assert len(df) == 4
        assert "IdNumber" in df.columns
        assert "Name" in df.columns
        assert "Fed" in df.columns

    def test_read_all_chunked(self, sample_sqlite_db):
        """Test reading data in chunks."""
        reader = SqliteReader(sample_sqlite_db)
        chunks = list(reader.read_all_chunked(chunk_size=2))
        reader.close()

        assert len(chunks) == 2
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == 4

    def test_get_schema(self, sample_sqlite_db):
        """Test getting table schema."""
        reader = SqliteReader(sample_sqlite_db)
        schema = reader.get_schema()
        reader.close()

        assert schema is not None
        assert "CREATE TABLE fide" in schema


class TestTxtReader:
    """Tests for TxtReader."""

    def test_read_columns(self, sample_txt_file):
        """Test reading specific columns from text file."""
        reader = TxtReader(sample_txt_file)
        df = reader.read_columns(["IdNumber", "Tit", "WTit", "OTit"])
        reader.close()

        assert len(df) == 4
        assert list(df.columns) == ["IdNumber", "Tit", "WTit", "OTit"]

    def test_read_all(self, sample_txt_file):
        """Test reading all data from text file."""
        reader = TxtReader(sample_txt_file)
        df = reader.read_all()
        reader.close()

        assert len(df) == 4
        assert "IdNumber" in df.columns
        assert "Name" in df.columns

    def test_read_all_chunked(self, sample_txt_file):
        """Test reading data in chunks from text file."""
        reader = TxtReader(sample_txt_file)
        chunks = list(reader.read_all_chunked(chunk_size=2))
        reader.close()

        assert len(chunks) == 2
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == 4

    def test_skip_malformed_lines(self, tmp_path):
        """Test that malformed lines are skipped with warnings."""
        txt_path = tmp_path / "malformed.txt"

        # Create properly formatted valid lines
        valid1 = _format_fide_line({"IdNumber": 1001, "Name": "Player One", "Fed": "USA", "Sex": "M", "Tit": "GM", "WTit": "", "OTit": "", "FOA": "", "SRtng": 2700, "SGm": 100, "SK": 40, "RRtng": 2650, "RGm": 50, "Rk": 35, "BRtng": 2600, "BGm": 30, "BK": 30, "BDay": "1990", "Flag": ""})
        valid2 = _format_fide_line({"IdNumber": 1002, "Name": "Player Two", "Fed": "RUS", "Sex": "F", "Tit": "", "WTit": "WGM", "OTit": "", "FOA": "", "SRtng": 2400, "SGm": 80, "SK": 20, "RRtng": 2350, "RGm": 40, "Rk": 18, "BRtng": 2300, "BGm": 20, "BK": 15, "BDay": "1985", "Flag": ""})

        with open(txt_path, "w", encoding=FIDE_ENCODING) as f:
            # Valid line
            f.write(valid1 + "\n")
            # Too short line
            f.write("short line\n")
            # Another valid line
            f.write(valid2 + "\n")

        reader = TxtReader(txt_path)
        df = reader.read_all()
        reader.close()

        # Should only have 2 valid rows
        assert len(df) == 2

    def test_skip_header_line(self, sample_txt_file):
        """Test that header line is skipped."""
        reader = TxtReader(sample_txt_file)
        df = reader.read_all()
        reader.close()

        # Header should not be included as data
        assert "ID Number" not in df["IdNumber"].astype(str).values


class TestXmlReader:
    """Tests for XmlReader."""

    def test_read_columns(self, sample_xml_file):
        """Test reading specific columns from XML file."""
        reader = XmlReader(sample_xml_file)
        df = reader.read_columns(["IdNumber", "Tit", "WTit", "OTit"])
        reader.close()

        assert len(df) == 4
        assert list(df.columns) == ["IdNumber", "Tit", "WTit", "OTit"]

    def test_read_all(self, sample_xml_file):
        """Test reading all data from XML file."""
        reader = XmlReader(sample_xml_file)
        df = reader.read_all()
        reader.close()

        assert len(df) == 4
        assert "IdNumber" in df.columns
        assert "Name" in df.columns

        # Check specific values
        gm_player = df[df["IdNumber"] == 1001].iloc[0]
        assert gm_player["Tit"] == "GM"
        assert gm_player["Fed"] == "USA"
        assert gm_player["SRtng"] == 2700

    def test_read_all_chunked(self, sample_xml_file):
        """Test reading data in chunks from XML file."""
        reader = XmlReader(sample_xml_file)
        chunks = list(reader.read_all_chunked(chunk_size=2))
        reader.close()

        assert len(chunks) == 2
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == 4

    def test_skip_malformed_elements(self, tmp_path):
        """Test that elements without fideid are skipped with warnings."""
        xml_path = tmp_path / "malformed.xml"

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("<playerslist>\n")
            # Valid player
            f.write(_build_player_xml({"IdNumber": 1001, "Name": "Player One", "Fed": "USA", "Sex": "M", "Tit": "GM", "WTit": "", "OTit": "", "FOA": "", "SRtng": 2700, "SGm": 100, "SK": 40, "RRtng": 2650, "RGm": 50, "Rk": 35, "BRtng": 2600, "BGm": 30, "BK": 30, "BDay": "1990", "Flag": ""}) + "\n")
            # Player without fideid
            f.write("<player><name>No ID Player</name><country>USA</country></player>\n")
            # Another valid player
            f.write(_build_player_xml({"IdNumber": 1002, "Name": "Player Two", "Fed": "RUS", "Sex": "F", "Tit": "", "WTit": "WGM", "OTit": "", "FOA": "", "SRtng": 2400, "SGm": 80, "SK": 20, "RRtng": 2350, "RGm": 40, "Rk": 18, "BRtng": 2300, "BGm": 20, "BK": 15, "BDay": "1985", "Flag": ""}) + "\n")
            f.write("</playerslist>\n")

        reader = XmlReader(xml_path)
        df = reader.read_all()
        reader.close()

        # Should only have 2 valid rows
        assert len(df) == 2
