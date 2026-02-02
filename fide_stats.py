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
    """
    input_path = args.input
    verbose = args.verbose

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    # --- Verify source file exists ---
    if not input_path.exists():
        print(f"Error: Input file not found at '{input_path}'", file=sys.stderr)
        sys.exit(1)

    reader = None

    try:
        # --- Create reader ---
        reader = get_reader(input_path, verbose=verbose)
        print(f"Reading data from '{input_path}'...")

        # Read all data
        df = reader.read_all()
        log(f"Loaded {len(df)} rows.")

        # Check required columns exist
        required_cols = [FEDERATION_COL, INACTIVE_FLAG_COL] + TITLE_COLS_PRIORITY
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(
                f"Error: Missing required columns: {missing_cols}",
                file=sys.stderr
            )
            sys.exit(1)

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if reader:
            reader.close()

    # --- Data Processing ---
    print("Processing player data...")

    # Consolidate Title: Pick the highest priority title available
    df["main_title"] = (
        df[TITLE_COLS_PRIORITY[0]]
        .fillna(df[TITLE_COLS_PRIORITY[1]])
        .fillna(df[TITLE_COLS_PRIORITY[2]])
    )
    df["main_title"] = df["main_title"].fillna("No Title").replace("", "No Title")

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


if __name__ == "__main__":
    args = parse_args()
    run_analysis(args)
