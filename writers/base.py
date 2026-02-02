"""
Base protocol for FIDE database writers.
"""

from typing import Optional, Protocol

import pandas as pd


class FideWriter(Protocol):
    """Protocol for writing FIDE player data to various formats."""

    def write(self, df: pd.DataFrame, schema: Optional[str] = None) -> None:
        """
        Write player data to the output file.

        Args:
            df: DataFrame containing player data
            schema: Optional CREATE TABLE SQL for SQLite (ignored by txt writer)
        """
        ...

    def close(self) -> None:
        """Close any open resources and finalize the file."""
        ...
