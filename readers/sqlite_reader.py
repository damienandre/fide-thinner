"""
SQLite reader for FIDE database.
"""

import pathlib
import sqlite3
from typing import Iterator, Optional, Union

import pandas as pd


class SqliteReader:
    """Reader for FIDE SQLite database files."""

    def __init__(self, file_path: Union[str, pathlib.Path], verbose: bool = False):
        """
        Initialize the SQLite reader.

        Args:
            file_path: Path to the SQLite database file
            verbose: Enable verbose logging
        """
        self.file_path = pathlib.Path(file_path)
        self.verbose = verbose
        self._conn: Optional[sqlite3.Connection] = None

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            self._log(f"Connecting to '{self.file_path}'...")
            self._conn = sqlite3.connect(self.file_path)
        return self._conn

    def read_titles_data(self) -> pd.DataFrame:
        """
        Read only the title-related columns for filtering.

        Returns:
            DataFrame with columns: IdNumber, Tit, WTit, OTit
        """
        self._log("Reading title data from SQLite...")
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT IdNumber, Tit, WTit, OTit FROM fide", conn
        )
        # Normalize by filling NaNs with empty strings
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
        conn = self._get_connection()
        iterator = pd.read_sql_query(
            "SELECT * FROM fide", conn, chunksize=chunk_size
        )
        chunk_num = 0
        for chunk in iterator:
            chunk_num += 1
            self._log(f"Read chunk {chunk_num} with {len(chunk)} rows.")
            yield chunk

    def read_all(self) -> pd.DataFrame:
        """
        Read all player data at once.

        Returns:
            DataFrame containing all player data
        """
        self._log("Reading all data from SQLite...")
        conn = self._get_connection()
        df = pd.read_sql_query("SELECT * FROM fide", conn)
        self._log(f"Read {len(df)} total rows.")
        return df

    def get_schema(self) -> Optional[str]:
        """
        Get the CREATE TABLE statement for the fide table.

        Returns:
            The CREATE TABLE SQL statement, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='fide';"
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._log("Closing SQLite connection.")
            self._conn.close()
            self._conn = None
