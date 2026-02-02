"""
Base protocol for FIDE database readers.
"""

from typing import Iterator, List, Optional, Protocol

import pandas as pd


class FideReader(Protocol):
    """Protocol for reading FIDE player data from various formats."""

    def read_columns(self, columns: List[str]) -> pd.DataFrame:
        """
        Read only specified columns from the data source.

        Args:
            columns: List of column names to read

        Returns:
            DataFrame with only the specified columns
        """
        ...

    def read_all_chunked(self, chunk_size: int = 100000) -> Iterator[pd.DataFrame]:
        """
        Read all player data in chunks for memory-efficient processing.

        Args:
            chunk_size: Number of rows per chunk

        Yields:
            DataFrames containing chunks of player data
        """
        ...

    def read_all(self) -> pd.DataFrame:
        """
        Read all player data at once.

        Returns:
            DataFrame containing all player data
        """
        ...

    def close(self) -> None:
        """Close any open resources."""
        ...
