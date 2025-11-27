"""
This script creates a thinned version of the FIDE players database.

It reads two source databases:
1. `fide.sqlite`: The main database of all FIDE registered players.
2. `players.sqlite`: A database containing a specific subset of players.

It generates a new database, `fide_thin.sqlite`, with the same structure
as `fide.sqlite`, containing only players who meet at least one of
the following criteria:
- The player has a FIDE title (i.e., 'Tit', 'WTit', or 'OTit' is not empty).
- The player's ID is referenced in the `players.sqlite` database
  (linking `fide.IdNumber` to `players.FideId`).
"""

import os
import pathlib
import sqlite3
import sys

import pandas as pd

# --- Database file configuration ---
FIDE_DB_PATH = pathlib.Path("data/fide.sqlite")
PLAYERS_DB_PATH = pathlib.Path("data/players.sqlite")
THIN_DB_PATH = pathlib.Path("data/fide_thin.sqlite")


def thin_fide_database():
    """
    Reads, filters, and creates the thinned FIDE database.
    """
    # --- Verify source files exist ---
    if not FIDE_DB_PATH.exists():
        print(f"Error: Source database '{FIDE_DB_PATH}' not found.", file=sys.stderr)
        sys.exit(1)
    if not PLAYERS_DB_PATH.exists():
        print(f"Error: Source database '{PLAYERS_DB_PATH}' not found.", file=sys.stderr)
        sys.exit(1)

    # --- Remove old destination file if it exists ---
    if THIN_DB_PATH.exists():
        print(f"Removing existing destination file: '{THIN_DB_PATH}'")
        os.remove(THIN_DB_PATH)

    fide_conn = None
    players_conn = None
    thin_conn = None

    try:
        # --- Connect to source databases ---
        print(f"Connecting to '{FIDE_DB_PATH}' and '{PLAYERS_DB_PATH}'...")
        fide_conn = sqlite3.connect(FIDE_DB_PATH)
        players_conn = sqlite3.connect(PLAYERS_DB_PATH)

        # --- 1. Get IDs of players with titles from fide.sqlite ---
        print("Step 1: Reading players with titles from 'fide.sqlite'...")
        df_fide_titles = pd.read_sql_query(
            "SELECT IdNumber, Tit, WTit, OTit FROM fide", fide_conn
        )

        # Normalize by filling NaNs with empty strings
        for col in ["Tit", "WTit", "OTit"]:
            df_fide_titles[col] = df_fide_titles[col].fillna("")

        # Create a boolean mask for players with any title
        titled_mask = (
            (df_fide_titles["Tit"] != "")
            | (df_fide_titles["WTit"] != "")
            | (df_fide_titles["OTit"] != "")
        )
        titled_ids = set(df_fide_titles.loc[titled_mask, "IdNumber"])
        print(f"Found {len(titled_ids)} players with a FIDE title.")

        # --- 2. Get IDs of players referenced in players.sqlite ---
        print("Step 2: Reading referenced player IDs from 'players.sqlite'...")
        df_players_ref = pd.read_sql_query("SELECT FideId FROM players", players_conn)
        referenced_ids = set(df_players_ref["FideId"].dropna().astype(int))
        print(f"Found {len(referenced_ids)} referenced players.")

        # --- 3. Combine IDs into a final set ---
        ids_to_keep = titled_ids.union(referenced_ids)
        print(f"Step 3: Total unique players to keep: {len(ids_to_keep)}")

        if not ids_to_keep:
            print("No players to keep. The output database will be empty.")
            # Still create an empty DB with the right schema
            df_thin = pd.DataFrame()
        else:
            # --- 4. Read full fide data and filter it ---
            print("Step 4: Filtering main FIDE data...")
            # Reading in chunks can be more memory-efficient for large files
            chunk_size = 100000
            fide_iterator = pd.read_sql_query(
                "SELECT * FROM fide", fide_conn, chunksize=chunk_size
            )

            filtered_chunks = []
            for chunk in fide_iterator:
                filtered_chunks.append(chunk[chunk["IdNumber"].isin(ids_to_keep)])

            df_thin = pd.concat(filtered_chunks)
            print(f"Filtered data contains {len(df_thin)} players.")

        # --- 5. Create new database and write filtered data ---
        print(f"Step 5: Creating new database '{THIN_DB_PATH}' and writing data...")
        thin_conn = sqlite3.connect(THIN_DB_PATH)

        # Get the CREATE TABLE statement from the original database
        fide_cursor = fide_conn.cursor()
        fide_cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='fide';"
        )
        create_table_sql = fide_cursor.fetchone()

        if create_table_sql is None:
            raise RuntimeError("Could not retrieve table schema from 'fide.sqlite'.")

        # Execute the CREATE TABLE statement in the new database
        thin_conn.execute(create_table_sql[0])

        # Write the filtered DataFrame to the new database
        if not df_thin.empty:
            df_thin.to_sql("fide", thin_conn, if_exists="append", index=False)

        print(f"Successfully created '{THIN_DB_PATH}' with {len(df_thin)} players.")

    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"A database error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # --- Clean up connections ---
        if fide_conn:
            fide_conn.close()
        if players_conn:
            players_conn.close()
        if thin_conn:
            thin_conn.close()
        print("Database connections closed.")


if __name__ == "__main__":
    thin_fide_database()
    thin_fide_database()
    thin_fide_database()
