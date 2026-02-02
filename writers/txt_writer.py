"""
Fixed-width text file writer for FIDE database.
"""

import pathlib
from typing import Optional, TextIO, Union

import pandas as pd

from fide_format import COLUMN_NAMES, FIDE_COLUMNS, FIDE_ENCODING


class TxtWriter:
    """Writer for FIDE fixed-width text files (players_list_foa.txt format)."""

    def __init__(self, file_path: Union[str, pathlib.Path], verbose: bool = False):
        """
        Initialize the text file writer.

        Args:
            file_path: Path to the output text file
            verbose: Enable verbose logging
        """
        self.file_path = pathlib.Path(file_path)
        self.verbose = verbose
        self._file: Optional[TextIO] = None
        self._rows_written: int = 0
        self._header_written: bool = False

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _ensure_file(self) -> TextIO:
        """Ensure the output file is open."""
        if self._file is None:
            self._log(f"Creating text file '{self.file_path}'...")
            self._file = open(self.file_path, "w", encoding=FIDE_ENCODING)
        return self._file

    def _write_header(self) -> None:
        """Write the header line to the file."""
        if self._header_written:
            return

        f = self._ensure_file()
        header_parts = []
        for col in FIDE_COLUMNS:
            # Use display name for header (ID Number instead of IdNumber)
            display_name = col.name
            if col.name == "IdNumber":
                display_name = "ID Number"
            header_parts.append(display_name.ljust(col.width))

        f.write("".join(header_parts).rstrip() + "\n")
        self._header_written = True

    def _format_row(self, row: pd.Series) -> str:
        """
        Format a single row as a fixed-width string.

        Args:
            row: Pandas Series containing the row data

        Returns:
            Formatted fixed-width string
        """
        parts = []
        for col in FIDE_COLUMNS:
            value = row.get(col.name, "")

            # Handle None/NaN values
            if pd.isna(value):
                value = ""
            else:
                value = str(value)

            # Pad or truncate to column width
            if len(value) > col.width:
                value = value[:col.width]
            else:
                value = value.ljust(col.width)

            parts.append(value)

        return "".join(parts).rstrip()

    def write(self, df: pd.DataFrame, schema: Optional[str] = None) -> None:
        """
        Write player data to the text file.

        Args:
            df: DataFrame containing player data
            schema: Ignored (only used by SQLite writer)
        """
        if df.empty:
            self._log("No data to write (empty DataFrame).")
            return

        self._write_header()
        f = self._ensure_file()

        self._log(f"Writing {len(df)} rows to text file...")

        for _, row in df.iterrows():
            line = self._format_row(row)
            f.write(line + "\n")
            self._rows_written += 1

        self._log(f"Total rows written: {self._rows_written}")

    def close(self) -> None:
        """Close the file."""
        if self._file is not None:
            self._log(f"Closing text file. Total rows written: {self._rows_written}")
            self._file.close()
            self._file = None
