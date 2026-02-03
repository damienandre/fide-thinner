"""Integration tests for fide_thinner and fide_stats."""

import sqlite3

import pandas as pd
import pytest

from fide_format import FIDE_COLUMNS, FIDE_ENCODING


def _format_fide_line(data: dict) -> str:
    """Format a row as a fixed-width FIDE line using column specs."""
    line = [" "] * 161  # MIN_LINE_LENGTH
    for col in FIDE_COLUMNS:
        value = str(data.get(col.name, ""))
        for i, char in enumerate(value[:col.width]):
            line[col.start + i] = char
    return "".join(line)


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a test data directory with sample databases."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create fide.sqlite
    fide_db = data_dir / "fide.sqlite"
    conn = sqlite3.connect(fide_db)
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

    # Test data: 2 titled players, 1 untitled referenced, 1 untitled unreferenced
    test_data = [
        (1001, "GM Player", "USA", "M", "GM", "", "", "", 2700, 100, 40, 2650, 50, 35, 2600, 30, 30, "1990", ""),
        (1002, "WGM Player", "RUS", "F", "", "WGM", "", "", 2400, 80, 20, 2350, 40, 18, 2300, 20, 15, "1985", ""),
        (1003, "Referenced Player", "GER", "M", "", "", "", "", 2200, 50, 15, 2150, 25, 12, 2100, 15, 10, "2000", ""),
        (1004, "Unreferenced Player", "FRA", "M", "", "", "", "", 1800, 20, 10, 1750, 10, 8, 1700, 5, 5, "2005", "i"),
    ]
    conn.executemany(
        "INSERT INTO fide VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        test_data
    )
    conn.commit()
    conn.close()

    # Create players.sqlite (references player 1003)
    players_db = data_dir / "players.sqlite"
    conn = sqlite3.connect(players_db)
    conn.execute("CREATE TABLE players (FideId INT)")
    conn.execute("INSERT INTO players VALUES (1003)")
    conn.commit()
    conn.close()

    return data_dir


@pytest.fixture
def test_txt_file(tmp_path):
    """Create a test text file."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    txt_path = data_dir / "fide.txt"

    # Test data: 2 titled players, 1 untitled referenced, 1 untitled unreferenced
    test_rows = [
        {"IdNumber": 1001, "Name": "GM Player", "Fed": "USA", "Sex": "M", "Tit": "GM", "WTit": "", "OTit": "", "FOA": "", "SRtng": 2700, "SGm": 100, "SK": 40, "RRtng": 2650, "RGm": 50, "Rk": 35, "BRtng": 2600, "BGm": 30, "BK": 30, "BDay": "1990", "Flag": ""},
        {"IdNumber": 1002, "Name": "WGM Player", "Fed": "RUS", "Sex": "F", "Tit": "", "WTit": "WGM", "OTit": "", "FOA": "", "SRtng": 2400, "SGm": 80, "SK": 20, "RRtng": 2350, "RGm": 40, "Rk": 18, "BRtng": 2300, "BGm": 20, "BK": 15, "BDay": "1985", "Flag": ""},
        {"IdNumber": 1003, "Name": "Referenced Player", "Fed": "GER", "Sex": "M", "Tit": "", "WTit": "", "OTit": "", "FOA": "", "SRtng": 2200, "SGm": 50, "SK": 15, "RRtng": 2150, "RGm": 25, "Rk": 12, "BRtng": 2100, "BGm": 15, "BK": 10, "BDay": "2000", "Flag": ""},
        {"IdNumber": 1004, "Name": "Unreferenced Player", "Fed": "FRA", "Sex": "M", "Tit": "", "WTit": "", "OTit": "", "FOA": "", "SRtng": 1800, "SGm": 20, "SK": 10, "RRtng": 1750, "RGm": 10, "Rk": 8, "BRtng": 1700, "BGm": 5, "BK": 5, "BDay": "2005", "Flag": "i"},
    ]

    with open(txt_path, "w", encoding=FIDE_ENCODING) as f:
        # Write header line
        header_data = {"IdNumber": "ID Number", "Name": "Name", "Fed": "Fed", "Sex": "Sex", "Tit": "Tit", "WTit": "WTit", "OTit": "OTit", "FOA": "FOA", "SRtng": "SRtng", "SGm": "SGm", "SK": "SK", "RRtng": "RRtng", "RGm": "RGm", "Rk": "Rk", "BRtng": "BRtng", "BGm": "BGm", "BK": "BK", "BDay": "BDay", "Flag": "Flag"}
        f.write(_format_fide_line(header_data) + "\n")
        # Write data lines
        for row in test_rows:
            f.write(_format_fide_line(row) + "\n")

    # Create players.sqlite
    players_db = data_dir / "players.sqlite"
    conn = sqlite3.connect(players_db)
    conn.execute("CREATE TABLE players (FideId INT)")
    conn.execute("INSERT INTO players VALUES (1003)")
    conn.commit()
    conn.close()

    return data_dir


class TestFideThinner:
    """Integration tests for fide_thinner.py."""

    def test_default_sqlite_to_sqlite(self, test_data_dir):
        """Test default behavior: SQLite input to SQLite output."""
        from fide_thinner import thin_fide_database
        import argparse

        args = argparse.Namespace(
            input=test_data_dir / "fide.sqlite",
            players=test_data_dir / "players.sqlite",
            output=test_data_dir / "fide_thin.sqlite",
            chunk_size=100000,
            verbose=False,
            referenced=True,
            titled=True
        )
        thin_fide_database(args)

        # Verify output
        output_db = test_data_dir / "fide_thin.sqlite"
        assert output_db.exists()

        conn = sqlite3.connect(output_db)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        # Should have 3 players: 2 titled + 1 referenced
        assert len(df) == 3
        assert set(df["IdNumber"]) == {1001, 1002, 1003}

    def test_txt_to_txt(self, test_txt_file):
        """Test text input to text output."""
        from fide_thinner import thin_fide_database
        import argparse

        args = argparse.Namespace(
            input=test_txt_file / "fide.txt",
            players=test_txt_file / "players.sqlite",
            output=test_txt_file / "fide_thin.txt",
            chunk_size=100000,
            verbose=False,
            referenced=True,
            titled=True
        )
        thin_fide_database(args)

        # Verify output
        output_txt = test_txt_file / "fide_thin.txt"
        assert output_txt.exists()

        with open(output_txt, "r", encoding=FIDE_ENCODING) as f:
            lines = f.readlines()

        # Header + 3 data lines
        assert len(lines) == 4

    def test_sqlite_to_txt(self, test_data_dir):
        """Test SQLite input to text output."""
        from fide_thinner import thin_fide_database
        import argparse

        args = argparse.Namespace(
            input=test_data_dir / "fide.sqlite",
            players=test_data_dir / "players.sqlite",
            output=test_data_dir / "fide_thin.txt",
            chunk_size=100000,
            verbose=False,
            referenced=True,
            titled=True
        )
        thin_fide_database(args)

        # Verify output
        output_txt = test_data_dir / "fide_thin.txt"
        assert output_txt.exists()

        with open(output_txt, "r", encoding=FIDE_ENCODING) as f:
            lines = f.readlines()

        # Header + 3 data lines
        assert len(lines) == 4

    def test_filter_titled_only(self, test_data_dir):
        """Test filtering with --no-referenced flag (only titled players)."""
        from fide_thinner import thin_fide_database
        import argparse

        args = argparse.Namespace(
            input=test_data_dir / "fide.sqlite",
            players=test_data_dir / "players.sqlite",
            output=test_data_dir / "fide_titled_only.sqlite",
            chunk_size=100000,
            verbose=False,
            referenced=False,
            titled=True
        )
        thin_fide_database(args)

        # Verify output
        output_db = test_data_dir / "fide_titled_only.sqlite"
        assert output_db.exists()

        conn = sqlite3.connect(output_db)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        # Should have only 2 titled players (1001: GM, 1002: WGM)
        assert len(df) == 2
        assert set(df["IdNumber"]) == {1001, 1002}

    def test_filter_referenced_only(self, test_data_dir):
        """Test filtering with --no-titled flag (only referenced players)."""
        from fide_thinner import thin_fide_database
        import argparse

        args = argparse.Namespace(
            input=test_data_dir / "fide.sqlite",
            players=test_data_dir / "players.sqlite",
            output=test_data_dir / "fide_referenced_only.sqlite",
            chunk_size=100000,
            verbose=False,
            referenced=True,
            titled=False
        )
        thin_fide_database(args)

        # Verify output
        output_db = test_data_dir / "fide_referenced_only.sqlite"
        assert output_db.exists()

        conn = sqlite3.connect(output_db)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        # Should have only 1 referenced player (1003)
        assert len(df) == 1
        assert set(df["IdNumber"]) == {1003}

    def test_filter_both_disabled_error(self):
        """Test that --no-referenced --no-titled raises an error."""
        from fide_thinner import parse_args
        import sys

        # Capture the SystemExit from argparse.error()
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["fide_thinner.py", "--no-referenced", "--no-titled"]
            parse_args()

        # argparse.error() exits with code 2
        assert exc_info.value.code == 2

    def test_default_behavior_unchanged(self, test_data_dir):
        """Test that default behavior (both filters enabled) remains the same."""
        from fide_thinner import thin_fide_database
        import argparse

        args = argparse.Namespace(
            input=test_data_dir / "fide.sqlite",
            players=test_data_dir / "players.sqlite",
            output=test_data_dir / "fide_default.sqlite",
            chunk_size=100000,
            verbose=False,
            referenced=True,
            titled=True
        )
        thin_fide_database(args)

        # Verify output
        output_db = test_data_dir / "fide_default.sqlite"
        assert output_db.exists()

        conn = sqlite3.connect(output_db)
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        conn.close()

        # Should have 3 players: 2 titled + 1 referenced (same as original behavior)
        assert len(df) == 3
        assert set(df["IdNumber"]) == {1001, 1002, 1003}


class TestFideStats:
    """Integration tests for fide_stats.py."""

    def test_stats_sqlite(self, test_data_dir, capsys):
        """Test statistics from SQLite file."""
        from fide_stats import run_analysis
        import argparse

        args = argparse.Namespace(
            input=test_data_dir / "fide.sqlite",
            verbose=False
        )
        run_analysis(args)

        captured = capsys.readouterr()
        assert "Player Status by Federation" in captured.out
        assert "Player Status by Title" in captured.out
        assert "USA" in captured.out
        assert "GM" in captured.out

    def test_stats_txt(self, test_txt_file, capsys):
        """Test statistics from text file."""
        from fide_stats import run_analysis
        import argparse

        args = argparse.Namespace(
            input=test_txt_file / "fide.txt",
            verbose=False
        )
        run_analysis(args)

        captured = capsys.readouterr()
        assert "Player Status by Federation" in captured.out
        assert "Player Status by Title" in captured.out
