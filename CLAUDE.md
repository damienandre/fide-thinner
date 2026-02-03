# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fide-thinner is a Python utility for filtering and analyzing FIDE (International Chess Federation) player databases. It supports both SQLite databases (~195 MB, ~1.8 million players) and fixed-width text files (`players_list_foa.txt`).

## Running the Scripts

This project uses `uv` for Python package management and script execution.

```bash
# Create filtered database (keeps only titled players + referenced players)
uv run fide_thinner.py                                    # Default: SQLite in/out
uv run fide_thinner.py -i data/fide.txt -o data/thin.txt  # Text file support
uv run fide_thinner.py -i data/fide.txt -o data/thin.sqlite  # Convert txt to sqlite

# Generate statistics by federation and title
uv run fide_stats.py                      # Default: SQLite input
uv run fide_stats.py -i data/fide.txt     # Text file input
```

Both scripts require `pandas` and `pytest` for testing.

## CLI Options

### fide_thinner.py
```
-i, --input      Input FIDE file (.sqlite or .txt). Default: data/fide.sqlite
-p, --players    Players reference database (SQLite only). Default: data/players.sqlite
-o, --output     Output file (.sqlite or .txt). Default: data/fide_thin.<input_ext>
--chunk-size     Chunk size for large files. Default: 100000
-v, --verbose    Enable verbose logging
```

### fide_stats.py
```
-i, --input      Input FIDE file (.sqlite or .txt). Default: data/fide.sqlite
-v, --verbose    Enable verbose logging
```

## Database Schema

The `fide` table in `data/fide.sqlite`:
- `IdNumber` - FIDE player ID (primary key)
- `Fed` - Federation/country code (3 chars)
- `Tit`, `WTit`, `OTit` - Standard, Women's, and Other titles
- `SRtng`, `RRtng`, `BRtng` - Standard, Rapid, Blitz ratings
- `Flag` - Status: empty=active, 'i'/'wi'=inactive

## Architecture

```
fide-thinner/
├── readers/           # Reader abstractions for different formats
│   ├── base.py        # FideReader Protocol
│   ├── sqlite_reader.py
│   └── txt_reader.py
├── writers/           # Writer abstractions for different formats
│   ├── base.py        # FideWriter Protocol
│   ├── sqlite_writer.py
│   └── txt_writer.py
├── fide_format.py     # Column specifications for fixed-width format
├── fide_thinner.py    # Main filtering script
├── fide_stats.py      # Statistics generation script
└── tests/             # Test suite
```

**fide_thinner.py**: Creates a filtered output containing players who either:
1. Have any FIDE title (Tit, WTit, or OTit non-empty)
2. Are referenced in `players.sqlite` (via FideId → IdNumber)

Uses chunked reading (100K rows) for memory efficiency.

**fide_stats.py**: Outputs two reports to stdout:
1. Active/Inactive player counts by federation
2. Active/Inactive player counts by title (consolidates Tit > WTit > OTit priority)

## Data Files

- `data/fide.sqlite` or `data/fide.txt` - Source FIDE database (required)
- `data/players.sqlite` - Reference player IDs (required by fide_thinner.py)
- `data/fide_thin.sqlite` or `data/fide_thin.txt` - Generated filtered output

## Testing

```bash
uv run pytest tests/
```
