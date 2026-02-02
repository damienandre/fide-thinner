"""
Base protocol for FIDE database readers.
"""

from typing import Iterator, Protocol

import pandas as pd


class FideReader(Protocol):
    """Protocol for reading FIDE player data from various formats."""

    def read_titles_data(self) -> pd.DataFrame:
        """
        Read only the title-related columns for filtering.

        Returns:
            DataFrame with columns: IdNumber, Tit, WTit, OTit
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
