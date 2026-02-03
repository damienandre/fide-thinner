"""
FIDE fixed-width text file format specification.

This module defines the column specifications for the FIDE players_list_foa.txt format.
The format uses fixed-width columns with specific positions and widths.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ColumnSpec:
    """Specification for a single column in the FIDE text format."""
    name: str       # Column name (matches SQLite column name)
    start: int      # Starting position (0-indexed)
    width: int      # Column width in characters

    @property
    def end(self) -> int:
        """Ending position (exclusive)."""
        return self.start + self.width


# FIDE fixed-width format column specifications
# Based on FIDE standard players_list_foa.txt format (January 2025)
FIDE_COLUMNS: List[ColumnSpec] = [
    ColumnSpec("IdNumber", 0, 15),
    ColumnSpec("Name", 15, 61),
    ColumnSpec("Fed", 76, 4),
    ColumnSpec("Sex", 80, 4),
    ColumnSpec("Tit", 84, 5),
    ColumnSpec("WTit", 89, 5),
    ColumnSpec("OTit", 94, 15),
    ColumnSpec("FOA", 109, 4),
    ColumnSpec("SRtng", 113, 6),
    ColumnSpec("SGm", 119, 4),
    ColumnSpec("SK", 123, 3),
    ColumnSpec("RRtng", 126, 6),
    ColumnSpec("RGm", 132, 4),
    ColumnSpec("Rk", 136, 3),
    ColumnSpec("BRtng", 139, 6),
    ColumnSpec("BGm", 145, 4),
    ColumnSpec("BK", 149, 3),
    ColumnSpec("BDay", 152, 6),
    ColumnSpec("Flag", 158, 4),
]

# Expected minimum line length (end of BK column - BDay and Flag may be truncated/missing)
# BK ends at position 152, so lines must be at least 152 chars to include all rating data
MIN_LINE_LENGTH = 152

# Text file encoding used by FIDE
FIDE_ENCODING = "latin-1"

# Column name to spec mapping for quick lookup
COLUMN_MAP = {col.name: col for col in FIDE_COLUMNS}

# All column names in order
COLUMN_NAMES = [col.name for col in FIDE_COLUMNS]

# Integer columns that should be parsed as integers
INTEGER_COLUMNS = {"IdNumber", "SRtng", "SGm", "SK", "RRtng", "RGm", "Rk", "BRtng", "BGm", "BK"}

# String columns (all non-integer columns)
STRING_COLUMNS = {col.name for col in FIDE_COLUMNS if col.name not in INTEGER_COLUMNS}


def generate_sqlite_schema() -> str:
    """
    Generate a CREATE TABLE SQL statement based on column specifications.

    This is used when converting from text format to SQLite, where no
    source schema is available.

    Returns:
        CREATE TABLE SQL statement for the fide table
    """
    column_defs = []
    for col in FIDE_COLUMNS:
        if col.name == "IdNumber":
            column_defs.append(f"{col.name} INT PRIMARY KEY")
        elif col.name in INTEGER_COLUMNS:
            column_defs.append(f"{col.name} INT")
        else:
            column_defs.append(f"{col.name} VARCHAR({col.width})")

    columns_sql = ",\n    ".join(column_defs)
    return f"CREATE TABLE fide (\n    {columns_sql}\n)"
