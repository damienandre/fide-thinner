"""
This script analyzes the FIDE players database (fide.sqlite) to extract
statistics on active and inactive players per federation and title.

It uses the provided schema for the 'fide' table:
CREATE TABLE fide(IdNumber INT PRIMARY KEY, Name VARCHAR(60), Fed VARCHAR(3), Sex VARCHAR(1), Tit VARCHAR(3),
                    WTit VARCHAR(4), OTit VARCHAR(4), FOA VARCHAR(3), SRtng INT, SGm INT, SK INT, RRtng INT, RGm INT, Rk INT,
                    BRtng INT, BGm INT, BK INT, BDay VARCHAR(4), Flag VARCHAR(4), Birthday DATE)

Assumptions for analysis:
- Player data is in the table named 'fide'.
- 'Fed' column indicates the player's federation.
- 'Tit', 'WTit', 'OTit' columns indicate titles; 'Tit' is prioritized, then 'WTit', then 'OTit'.
- 'Flag' column indicates player status; non-empty 'Flag' means inactive, empty or NULL means active.

The script uses pandas for data manipulation and assumes it is installed.
"""

import pathlib
import sqlite3
import sys

import pandas as pd

# --- Configuration ---
DB_FILE = pathlib.Path("data/fide.sqlite")
PLAYER_TABLE = "fide"
FEDERATION_COL = "Fed"
TITLE_COLS_PRIORITY = ["Tit", "WTit", "OTit"]  # Ordered by priority
INACTIVE_FLAG_COL = "Flag"


def run_analysis():
    """
    Connects to the SQLite database, extracts player data based on the provided schema,
    and prints statistics about active/inactive players by federation and title.
    """
    if not DB_FILE.exists():
        print(f"Error: Database file not found at '{DB_FILE}'", file=sys.stderr)
        sys.exit(1)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            print(f"Successfully connected to {DB_FILE}")

            # Check if the table exists
            query_table_exists = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{PLAYER_TABLE}';"
            if pd.read_sql_query(query_table_exists, conn).empty:
                print(
                    f"Error: Table '{PLAYER_TABLE}' not found in the database.",
                    file=sys.stderr,
                )
                all_tables = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table';", conn
                )
                print("Available tables are:", file=sys.stderr)
                print(all_tables.to_string(index=False), file=sys.stderr)
                sys.exit(1)

            # Construct the SELECT query with all necessary columns
            columns_to_select = [
                FEDERATION_COL,
                INACTIVE_FLAG_COL,
            ] + TITLE_COLS_PRIORITY
            columns_str = ", ".join([f'"{col}"' for col in columns_to_select])

            print(
                f"Reading data from table '{PLAYER_TABLE}' with columns: {columns_str}..."
            )
            df = pd.read_sql_query(f'SELECT {columns_str} FROM "{PLAYER_TABLE}"', conn)

    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Catch pandas errors if columns are missing
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        print(
            f"Please ensure table '{PLAYER_TABLE}' has '{FEDERATION_COL}', '{INACTIVE_FLAG_COL}', "
            f"and {'/'.join(TITLE_COLS_PRIORITY)} columns as specified in the schema.",
            file=sys.stderr,
        )
        sys.exit(1)

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
    # As clarified by the user, 'i' or 'wi' in the Flag column means inactive.
    df['is_inactive'] = df[INACTIVE_FLAG_COL].isin(['i', 'wi'])

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
    run_analysis()
    run_analysis()
    run_analysis()
