"""
FIDE database writer factory.

Provides a factory function to get the appropriate writer based on file extension.
"""

import pathlib
from typing import Union

from .base import FideWriter
from .sqlite_writer import SqliteWriter
from .txt_writer import TxtWriter
from .xml_writer import XmlWriter


def get_writer(file_path: Union[str, pathlib.Path], verbose: bool = False) -> FideWriter:
    """
    Get the appropriate writer for the given file path.

    Args:
        file_path: Path to the output FIDE database file (.xml, .sqlite, or .txt)
        verbose: Enable verbose logging

    Returns:
        A FideWriter instance appropriate for the file type

    Raises:
        ValueError: If the file extension is not supported
    """
    path = pathlib.Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".sqlite":
        return SqliteWriter(path, verbose=verbose)
    elif suffix == ".txt":
        return TxtWriter(path, verbose=verbose)
    elif suffix == ".xml":
        return XmlWriter(path, verbose=verbose)
    else:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. "
            "Supported extensions: .xml, .sqlite, .txt"
        )


__all__ = ["get_writer", "FideWriter", "SqliteWriter", "TxtWriter", "XmlWriter"]
