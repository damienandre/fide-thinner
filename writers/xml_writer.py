"""
XML file writer for FIDE database.
"""

import pathlib
import sys
import xml.etree.ElementTree as ET
from typing import IO, Optional, Union

import pandas as pd

from fide_format import COLUMN_NAMES, REVERSE_XML_TAG_MAP


class XmlWriter:
    """Writer for FIDE XML files (players_list_xml_foa.xml format)."""

    def __init__(self, file_path: Union[str, pathlib.Path], verbose: bool = False):
        """
        Initialize the XML file writer.

        Args:
            file_path: Path to the output XML file
            verbose: Enable verbose logging
        """
        self.file_path = pathlib.Path(file_path)
        self.verbose = verbose
        self._file: Optional[IO[bytes]] = None
        self._rows_written: int = 0
        self._header_written: bool = False

    def __enter__(self) -> "XmlWriter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures file is closed."""
        self.close()

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _warn(self, message: str) -> None:
        """Print a warning message to stderr."""
        print(f"Warning: {message}", file=sys.stderr)

    def _ensure_file(self) -> IO[bytes]:
        """Ensure the output file is open and header is written."""
        if self._file is None:
            self._log(f"Creating XML file '{self.file_path}'...")
            self._file = open(self.file_path, "wb")
        if not self._header_written:
            self._file.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            self._file.write(b"<playerslist>\n")
            self._header_written = True
        return self._file

    def write(self, df: pd.DataFrame, schema: Optional[str] = None) -> None:
        """
        Write player data to the XML file.

        Args:
            df: DataFrame containing player data
            schema: Ignored (only used by SQLite writer)
        """
        if df.empty:
            self._log("No data to write (empty DataFrame).")
            return

        f = self._ensure_file()
        self._log(f"Writing {len(df)} rows to XML file...")

        column_indices = {col: i for i, col in enumerate(df.columns)}

        for row_tuple in df.itertuples(index=False, name=None):
            player_elem = ET.Element("player")

            for col_name in COLUMN_NAMES:
                xml_tag = REVERSE_XML_TAG_MAP.get(col_name)
                if xml_tag is None:
                    continue

                idx = column_indices.get(col_name)
                if idx is None:
                    continue

                value = row_tuple[idx]

                if pd.isna(value):
                    value_str = ""
                else:
                    value_str = str(value)
                    # Clean up integer formatting (remove .0)
                    if value_str.endswith(".0"):
                        value_str = value_str[:-2]

                child = ET.SubElement(player_elem, xml_tag)
                child.text = value_str

            xml_str = ET.tostring(player_elem, encoding="unicode")
            f.write((xml_str + "\n").encode("utf-8"))
            self._rows_written += 1

        self._log(f"Total rows written: {self._rows_written}")

    def close(self) -> None:
        """Close the file and write the closing tag."""
        if self._file is not None:
            if self._header_written:
                self._file.write(b"</playerslist>\n")
            self._log(f"Closing XML file. Total rows written: {self._rows_written}")
            self._file.close()
            self._file = None
