"""
FIDE database reader factory.

Provides a factory function to get the appropriate reader based on file extension.
"""

import pathlib
from typing import Union

from .base import FideReader
from .sqlite_reader import SqliteReader
from .txt_reader import TxtReader
from .xml_reader import XmlReader


def get_reader(file_path: Union[str, pathlib.Path], verbose: bool = False) -> FideReader:
    """
    Get the appropriate reader for the given file path.

    Args:
        file_path: Path to the FIDE database file (.xml, .sqlite, or .txt)
        verbose: Enable verbose logging

    Returns:
        A FideReader instance appropriate for the file type

    Raises:
        ValueError: If the file extension is not supported
    """
    path = pathlib.Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".sqlite":
        return SqliteReader(path, verbose=verbose)
    elif suffix == ".txt":
        return TxtReader(path, verbose=verbose)
    elif suffix == ".xml":
        return XmlReader(path, verbose=verbose)
    else:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. "
            "Supported extensions: .xml, .sqlite, .txt"
        )


__all__ = ["get_reader", "FideReader", "SqliteReader", "TxtReader", "XmlReader"]
