"""
Fixed-width text file reader for FIDE database.
"""

import pathlib
import sys
from typing import Iterator, List, Optional, Union

import pandas as pd

from fide_format import (
    COLUMN_NAMES,
    FIDE_COLUMNS,
    FIDE_ENCODING,
    INTEGER_COLUMNS,
    MIN_LINE_LENGTH,
)


class TxtReader:
    """Reader for FIDE fixed-width text files (players_list_foa.txt format)."""

    def __init__(self, file_path: Union[str, pathlib.Path], verbose: bool = False):
        """
        Initialize the text file reader.

        Args:
            file_path: Path to the FIDE text file
            verbose: Enable verbose logging
        """
        self.file_path = pathlib.Path(file_path)
        self.verbose = verbose
        self._skipped_lines: int = 0
        self._total_lines: int = 0

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _warn(self, message: str) -> None:
        """Print a warning message to stderr."""
        print(f"Warning: {message}", file=sys.stderr)

    def _parse_line(self, line: str, line_num: int) -> Optional[dict]:
        """
        Parse a single line of the fixed-width format.

        Args:
            line: The line to parse
            line_num: Line number for error reporting

        Returns:
            Dictionary of column values, or None if the line is malformed
        """
        # Skip header line (contains "ID Number" text)
        if "ID Number" in line or line.strip() == "":
            return None

        # Check minimum line length
        if len(line) < MIN_LINE_LENGTH:
            self._warn(f"Line {line_num}: Too short ({len(line)} chars), skipping.")
            self._skipped_lines += 1
            return None

        try:
            row = {}
            for col in FIDE_COLUMNS:
                value = line[col.start:col.end].strip()

                if col.name in INTEGER_COLUMNS:
                    # Parse integer columns, treat empty as None
                    if value == "":
                        row[col.name] = None
                    else:
                        row[col.name] = int(value)
                else:
                    # String columns
                    row[col.name] = value

            # Validate IdNumber is present and valid
            if row.get("IdNumber") is None:
                self._warn(f"Line {line_num}: Missing or invalid IdNumber, skipping.")
                self._skipped_lines += 1
                return None

            return row

        except ValueError as e:
            self._warn(f"Line {line_num}: Parse error ({e}), skipping.")
            self._skipped_lines += 1
            return None

    def _read_lines(self) -> Iterator[str]:
        """Read lines from the file."""
        with open(self.file_path, "r", encoding=FIDE_ENCODING) as f:
            for line in f:
                yield line.rstrip("\n\r")

    def _finalize(self) -> None:
        """Report skipped lines if any."""
        if self._skipped_lines > 0:
            self._warn(
                f"Total skipped lines: {self._skipped_lines} out of {self._total_lines}"
            )

    def read_titles_data(self) -> pd.DataFrame:
        """
        Read only the title-related columns for filtering.

        Returns:
            DataFrame with columns: IdNumber, Tit, WTit, OTit
        """
        self._log(f"Reading title data from '{self.file_path}'...")
        self._skipped_lines = 0
        self._total_lines = 0

        rows: List[dict] = []

        for line_num, line in enumerate(self._read_lines(), start=1):
            self._total_lines = line_num
            parsed = self._parse_line(line, line_num)
            if parsed is not None:
                rows.append({
                    "IdNumber": parsed["IdNumber"],
                    "Tit": parsed["Tit"],
                    "WTit": parsed["WTit"],
                    "OTit": parsed["OTit"],
                })

        self._finalize()
        df = pd.DataFrame(rows, columns=["IdNumber", "Tit", "WTit", "OTit"])
        # Ensure string columns have empty string instead of NaN
        for col in ["Tit", "WTit", "OTit"]:
            df[col] = df[col].fillna("")
        self._log(f"Read {len(df)} rows of title data.")
        return df

    def read_all_chunked(self, chunk_size: int = 100000) -> Iterator[pd.DataFrame]:
        """
        Read all player data in chunks for memory-efficient processing.

        Args:
            chunk_size: Number of rows per chunk

        Yields:
            DataFrames containing chunks of player data
        """
        self._log(f"Reading all data in chunks of {chunk_size}...")
        self._skipped_lines = 0
        self._total_lines = 0

        chunk_rows: List[dict] = []
        chunk_num = 0

        for line_num, line in enumerate(self._read_lines(), start=1):
            self._total_lines = line_num
            parsed = self._parse_line(line, line_num)
            if parsed is not None:
                chunk_rows.append(parsed)

                if len(chunk_rows) >= chunk_size:
                    chunk_num += 1
                    self._log(f"Yielding chunk {chunk_num} with {len(chunk_rows)} rows.")
                    yield pd.DataFrame(chunk_rows, columns=COLUMN_NAMES)
                    chunk_rows = []

        # Yield remaining rows
        if chunk_rows:
            chunk_num += 1
            self._log(f"Yielding final chunk {chunk_num} with {len(chunk_rows)} rows.")
            yield pd.DataFrame(chunk_rows, columns=COLUMN_NAMES)

        self._finalize()

    def read_all(self) -> pd.DataFrame:
        """
        Read all player data at once.

        Returns:
            DataFrame containing all player data
        """
        self._log(f"Reading all data from '{self.file_path}'...")
        self._skipped_lines = 0
        self._total_lines = 0

        rows: List[dict] = []

        for line_num, line in enumerate(self._read_lines(), start=1):
            self._total_lines = line_num
            parsed = self._parse_line(line, line_num)
            if parsed is not None:
                rows.append(parsed)

        self._finalize()
        df = pd.DataFrame(rows, columns=COLUMN_NAMES)
        self._log(f"Read {len(df)} total rows.")
        return df

    def close(self) -> None:
        """Close any open resources (no-op for text files)."""
        pass
