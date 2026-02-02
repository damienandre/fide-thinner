"""
This script creates a thinned version of the FIDE players database.

It reads two source databases:
1. A FIDE players file (SQLite or fixed-width text format)
2. `players.sqlite`: A database containing a specific subset of players.

It generates a new database (SQLite or text), with the same structure
as the input, containing only players who meet at least one of
the following criteria:
- The player has a FIDE title (i.e., 'Tit', 'WTit', or 'OTit' is not empty).
- The player's ID is referenced in the `players.sqlite` database
  (linking `fide.IdNumber` to `players.FideId`).
"""

import argparse
import pathlib
import sqlite3
import sys

import pandas as pd

from fide_format import generate_sqlite_schema
from readers import get_reader
from writers import get_writer

# --- Default file paths ---
DEFAULT_FIDE_INPUT = pathlib.Path("data/fide.sqlite")
DEFAULT_PLAYERS_DB = pathlib.Path("data/players.sqlite")
DEFAULT_OUTPUT = pathlib.Path("data/fide_thin.sqlite")


class FideProcessingError(Exception):
    """Exception raised for errors during FIDE database processing."""
    pass


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create a thinned version of the FIDE players database."
    )
    parser.add_argument(
        "-i", "--input",
        type=pathlib.Path,
        default=DEFAULT_FIDE_INPUT,
        help=f"Input FIDE file (.sqlite or .txt). Default: {DEFAULT_FIDE_INPUT}"
    )
    parser.add_argument(
        "-p", "--players",
        type=pathlib.Path,
        default=DEFAULT_PLAYERS_DB,
        help=f"Players reference database (SQLite only). Default: {DEFAULT_PLAYERS_DB}"
    )
    parser.add_argument(
        "-o", "--output",
        type=pathlib.Path,
        default=None,
        help="Output file (.sqlite or .txt). Default: data/fide_thin.<input_ext>"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100000,
        help="Chunk size for processing large files. Default: 100000"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Validate chunk-size
    if args.chunk_size <= 0:
        parser.error("--chunk-size must be a positive integer")

    return args


def get_default_output(input_path: pathlib.Path) -> pathlib.Path:
    """Get default output path based on input file extension."""
    suffix = input_path.suffix.lower()
    return pathlib.Path(f"data/fide_thin{suffix}")


def get_referenced_ids(players_db_path: pathlib.Path, verbose: bool = False) -> set:
    """
    Get the set of FIDE IDs referenced in the players database.

    Args:
        players_db_path: Path to the players.sqlite database
        verbose: Enable verbose logging

    Returns:
        Set of referenced FIDE IDs

    Raises:
        FideProcessingError: If database access fails
    """
    if verbose:
        print(f"Reading referenced player IDs from '{players_db_path}'...")

    try:
        with sqlite3.connect(players_db_path) as conn:
            df = pd.read_sql_query("SELECT FideId FROM players", conn)
            referenced_ids = set(df["FideId"].dropna().astype(int))
    except sqlite3.Error as e:
        raise FideProcessingError(f"Failed to read players database: {e}")

    if verbose:
        print(f"Found {len(referenced_ids)} referenced players.")

    return referenced_ids


def thin_fide_database(args: argparse.Namespace) -> None:
    """
    Reads, filters, and creates the thinned FIDE database.

    Performs single-pass reading: collects titled player IDs during the first
    chunk pass, then filters all chunks in one read through the file.

    Raises:
        FideProcessingError: If processing fails
    """
    input_path = args.input
    players_path = args.players
    output_path = args.output if args.output else get_default_output(input_path)
    chunk_size = args.chunk_size
    verbose = args.verbose

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    # --- Verify source files exist ---
    if not input_path.exists():
        raise FideProcessingError(f"Source file '{input_path}' not found.")
    if not players_path.exists():
        raise FideProcessingError(f"Players database '{players_path}' not found.")

    reader = None
    writer = None

    try:
        # --- Create reader and writer ---
        reader = get_reader(input_path, verbose=verbose)
        writer = get_writer(output_path, verbose=verbose)

        # --- Get referenced IDs from players.sqlite ---
        print("Step 1: Reading referenced player IDs...")
        referenced_ids = get_referenced_ids(players_path, verbose=verbose)
        print(f"Found {len(referenced_ids)} referenced players.")

        # --- Single-pass: read chunks, collect titled IDs, and filter ---
        print("Step 2: Processing FIDE data (single pass)...")

        # Get schema for SQLite writer
        # Use source schema if available, otherwise generate from format spec
        schema = None
        if hasattr(reader, "get_schema"):
            schema = reader.get_schema()
        if schema is None and output_path.suffix.lower() == ".sqlite":
            log("Generating schema from column specifications...")
            schema = generate_sqlite_schema()

        titled_ids: set = set()
        total_written = 0
        pending_chunks: list = []

        # First pass: collect all titled IDs while reading chunks
        for chunk in reader.read_all_chunked(chunk_size):
            # Find titled players in this chunk
            titled_mask = (
                (chunk["Tit"].fillna("") != "")
                | (chunk["WTit"].fillna("") != "")
                | (chunk["OTit"].fillna("") != "")
            )
            chunk_titled_ids = set(chunk.loc[titled_mask, "IdNumber"])
            titled_ids.update(chunk_titled_ids)
            pending_chunks.append(chunk)

        print(f"Found {len(titled_ids)} players with a FIDE title.")

        # Combine IDs to keep
        ids_to_keep = titled_ids.union(referenced_ids)
        print(f"Step 3: Total unique players to keep: {len(ids_to_keep)}")

        if not ids_to_keep:
            print("No players to keep. The output file will be empty.")
        else:
            # Second pass: filter and write pending chunks
            print("Step 4: Writing filtered data...")
            for chunk in pending_chunks:
                filtered_chunk = chunk[chunk["IdNumber"].isin(ids_to_keep)]
                if not filtered_chunk.empty:
                    writer.write(filtered_chunk, schema=schema)
                    total_written += len(filtered_chunk)
                    # Only pass schema for the first chunk
                    schema = None

            print(f"Filtered data contains {total_written} players.")

        # --- Finalize ---
        print(f"Step 5: Finalizing output file '{output_path}'...")
        print(f"Successfully created '{output_path}'.")

    except ValueError as e:
        raise FideProcessingError(f"Configuration error: {e}")
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        raise FideProcessingError(f"Database error: {e}")
    finally:
        # --- Clean up resources ---
        if reader:
            reader.close()
        if writer:
            writer.close()
        log("Resources cleaned up.")


def main() -> None:
    """Main entry point with error handling."""
    args = parse_args()
    try:
        thin_fide_database(args)
    except FideProcessingError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
