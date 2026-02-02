"""
SQLite writer for FIDE database.
"""

import os
import pathlib
import sqlite3
from typing import Optional, Union

import pandas as pd


class SqliteWriter:
    """Writer for FIDE SQLite database files."""

    def __init__(self, file_path: Union[str, pathlib.Path], verbose: bool = False):
        """
        Initialize the SQLite writer.

        Args:
            file_path: Path to the output SQLite database file
            verbose: Enable verbose logging
        """
        self.file_path = pathlib.Path(file_path)
        self.verbose = verbose
        self._conn: Optional[sqlite3.Connection] = None
        self._schema_created = False

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _ensure_clean(self) -> None:
        """Remove existing file if present."""
        if self.file_path.exists():
            self._log(f"Removing existing file: '{self.file_path}'")
            os.remove(self.file_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            self._ensure_clean()
            self._log(f"Creating database '{self.file_path}'...")
            self._conn = sqlite3.connect(self.file_path)
        return self._conn

    def write(self, df: pd.DataFrame, schema: Optional[str] = None) -> None:
        """
        Write player data to the SQLite database.

        Args:
            df: DataFrame containing player data
            schema: Optional CREATE TABLE SQL statement to use for the table schema.
                    If provided, it will be executed before writing data.
        """
        conn = self._get_connection()

        # Create schema if provided and not already created
        if schema is not None and not self._schema_created:
            self._log("Creating table schema...")
            conn.execute(schema)
            self._schema_created = True

        # Write data
        if not df.empty:
            self._log(f"Writing {len(df)} rows to database...")
            df.to_sql("fide", conn, if_exists="append", index=False)
            self._log(f"Successfully wrote {len(df)} rows.")
        else:
            self._log("No data to write (empty DataFrame).")

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._log("Closing SQLite connection.")
            self._conn.close()
            self._conn = None
