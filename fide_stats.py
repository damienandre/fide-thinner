"""
This script analyzes the FIDE players database to extract statistics on
active and inactive players per federation and title.

It supports both SQLite databases and fixed-width text files.

Assumptions for analysis:
- 'Fed' column indicates the player's federation.
- 'Tit', 'WTit', 'OTit' columns indicate titles; 'Tit' is prioritized, then 'WTit', then 'OTit'.
- 'Flag' column indicates player status; 'i' or 'wi' means inactive, empty means active.

The script uses pandas for data manipulation.
"""

import argparse
import pathlib
import sys

import pandas as pd

from readers import get_reader

# --- Default configuration ---
DEFAULT_INPUT = pathlib.Path("data/fide.sqlite")
FEDERATION_COL = "Fed"
TITLE_COLS_PRIORITY = ["Tit", "WTit", "OTit"]
INACTIVE_FLAG_COL = "Flag"
REQUIRED_COLUMNS = [FEDERATION_COL, INACTIVE_FLAG_COL] + TITLE_COLS_PRIORITY


class StatsError(Exception):
    """Exception raised for errors during statistics processing."""
    pass


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze FIDE players database for statistics by federation and title."
    )
    parser.add_argument(
        "-i", "--input",
        type=pathlib.Path,
        default=DEFAULT_INPUT,
        help=f"Input FIDE file (.sqlite or .txt). Default: {DEFAULT_INPUT}"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


def run_analysis(args: argparse.Namespace) -> None:
    """
    Load player data and print statistics about active/inactive players
    by federation and title.

    Raises:
        StatsError: If analysis fails
    """
    input_path = args.input
    verbose = args.verbose

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    # --- Verify source file exists ---
    if not input_path.exists():
        raise StatsError(f"Input file not found at '{input_path}'")

    reader = None

    try:
        # --- Create reader ---
        reader = get_reader(input_path, verbose=verbose)
        print(f"Reading data from '{input_path}'...")

        # Read only required columns for efficiency
        df = reader.read_columns(REQUIRED_COLUMNS)
        log(f"Loaded {len(df)} rows.")

    except ValueError as e:
        raise StatsError(f"Configuration error: {e}")
    except Exception as e:
        raise StatsError(f"Failed to read data: {e}")
    finally:
        if reader:
            reader.close()

    # --- Data Processing ---
    print("Processing player data...")

    # Normalize title columns - ensure empty strings instead of NaN
    for col in TITLE_COLS_PRIORITY:
        df[col] = df[col].fillna("")

    # Consolidate Title: Pick the highest priority non-empty title
    # Use explicit iteration to handle empty strings (fillna only handles NaN)
    df["main_title"] = "No Title"
    for col in reversed(TITLE_COLS_PRIORITY):  # Process in reverse priority order
        mask = df[col] != ""
        df.loc[mask, "main_title"] = df.loc[mask, col]

    # Determine Active/Inactive status from 'Flag' column
    # 'i' or 'wi' in the Flag column means inactive.
    df["is_inactive"] = df[INACTIVE_FLAG_COL].isin(["i", "wi"])

    # --- Federation Statistics ---
    print("\n--- Player Status by Federation ---")
    fed_stats = (
        df.groupby(FEDERATION_COL)["is_inactive"].value_counts().unstack(fill_value=0)
    )
    fed_stats = fed_stats.rename(columns={False: "Active", True: "Inactive"})
    if "Active" not in fed_stats:
        fed_stats["Active"] = 0
    if "Inactive" not in fed_stats:
        fed_stats["Inactive"] = 0
    fed_stats["Total"] = fed_stats["Active"] + fed_stats["Inactive"]
    fed_stats = fed_stats.sort_values(by="Total", ascending=False)
    print(fed_stats.to_string())

    # --- Title Statistics ---
    print("\n\n--- Player Status by Title ---")
    title_stats = (
        df.groupby("main_title")["is_inactive"].value_counts().unstack(fill_value=0)
    )
    title_stats = title_stats.rename(columns={False: "Active", True: "Inactive"})
    if "Active" not in title_stats:
        title_stats["Active"] = 0
    if "Inactive" not in title_stats:
        title_stats["Inactive"] = 0
    title_stats["Total"] = title_stats["Active"] + title_stats["Inactive"]
    title_stats = title_stats.sort_values(by="Total", ascending=False)
    print(title_stats.to_string())

    print("\n\nAnalysis complete.")


def main() -> None:
    """Main entry point with error handling."""
    args = parse_args()
    try:
        run_analysis(args)
    except StatsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
