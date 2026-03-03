"""
XML file reader for FIDE database.
"""

import pathlib
import sys
import xml.etree.ElementTree as ET
from typing import Iterator, List, Optional, Set, Union

import pandas as pd

from fide_format import COLUMN_NAMES, INTEGER_COLUMNS, XML_TAG_MAP


class XmlReader:
    """Reader for FIDE XML files (players_list_xml_foa.xml format)."""

    def __init__(self, file_path: Union[str, pathlib.Path], verbose: bool = False):
        """
        Initialize the XML file reader.

        Args:
            file_path: Path to the FIDE XML file
            verbose: Enable verbose logging
        """
        self.file_path = pathlib.Path(file_path)
        self.verbose = verbose
        self._skipped_elements: int = 0
        self._total_elements: int = 0

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _warn(self, message: str) -> None:
        """Print a warning message to stderr."""
        print(f"Warning: {message}", file=sys.stderr)

    def _parse_player(
        self, player_elem: ET.Element, columns: Optional[Set[str]] = None
    ) -> Optional[dict]:
        """
        Parse a single <player> element.

        Args:
            player_elem: The <player> XML element
            columns: Optional set of column names to parse. If None, parse all.

        Returns:
            Dictionary of column values, or None if the element is malformed
        """
        try:
            row: dict = {}

            for child in player_elem:
                col_name = XML_TAG_MAP.get(child.tag)
                if col_name is None:
                    continue
                if columns is not None and col_name not in columns:
                    continue

                text = child.text.strip() if child.text else ""

                if col_name in INTEGER_COLUMNS:
                    if text == "":
                        row[col_name] = None
                    else:
                        row[col_name] = int(text)
                else:
                    row[col_name] = text

            # Validate IdNumber is present and valid
            if "IdNumber" not in row or row["IdNumber"] is None:
                self._warn(
                    f"Element {self._total_elements}: Missing or invalid fideid, skipping."
                )
                self._skipped_elements += 1
                return None

            return row

        except ValueError as e:
            self._warn(f"Element {self._total_elements}: Parse error ({e}), skipping.")
            self._skipped_elements += 1
            return None

    def _iter_players(self) -> Iterator[ET.Element]:
        """Iterate over <player> elements using streaming parsing."""
        for event, elem in ET.iterparse(self.file_path, events=("end",)):
            if elem.tag == "player":
                yield elem
                elem.clear()

    def _finalize(self) -> None:
        """Report skipped elements if any."""
        if self._skipped_elements > 0:
            self._warn(
                f"Total skipped elements: {self._skipped_elements} "
                f"out of {self._total_elements}"
            )

    def read_columns(self, columns: List[str]) -> pd.DataFrame:
        """
        Read only specified columns from the file.

        Args:
            columns: List of column names to read

        Returns:
            DataFrame with only the specified columns
        """
        self._log(f"Reading columns {columns} from '{self.file_path}'...")
        self._skipped_elements = 0
        self._total_elements = 0

        columns_set = set(columns)
        # Ensure IdNumber is included for validation
        columns_set.add("IdNumber")
        output_columns = list(columns)

        rows: List[dict] = []

        for player_elem in self._iter_players():
            self._total_elements += 1
            parsed = self._parse_player(player_elem, columns_set)
            if parsed is not None:
                rows.append({col: parsed.get(col, "") for col in output_columns})

        self._finalize()
        df = pd.DataFrame(rows, columns=output_columns)
        self._log(f"Read {len(df)} rows.")
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
        self._skipped_elements = 0
        self._total_elements = 0

        chunk_rows: List[dict] = []
        chunk_num = 0

        for player_elem in self._iter_players():
            self._total_elements += 1
            parsed = self._parse_player(player_elem)
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
        self._skipped_elements = 0
        self._total_elements = 0

        rows: List[dict] = []

        for player_elem in self._iter_players():
            self._total_elements += 1
            parsed = self._parse_player(player_elem)
            if parsed is not None:
                rows.append(parsed)

        self._finalize()
        df = pd.DataFrame(rows, columns=COLUMN_NAMES)
        self._log(f"Read {len(df)} total rows.")
        return df

    def close(self) -> None:
        """Close any open resources (no-op for XML files)."""
        pass
