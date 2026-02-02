# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fide-thinner is a Python utility for filtering and analyzing FIDE (International Chess Federation) player databases. It processes a ~195 MB SQLite database containing ~1.8 million chess players.

## Running the Scripts

```bash
# Create filtered database (keeps only titled players + referenced players)
python fide_thinner.py

# Generate statistics by federation and title
python fide_stats.py
```

Both scripts require `pandas` (not listed in pyproject.toml dependencies but required).

## Database Schema

The `fide` table in `data/fide.sqlite`:
- `IdNumber` - FIDE player ID (primary key)
- `Fed` - Federation/country code (3 chars)
- `Tit`, `WTit`, `OTit` - Standard, Women's, and Other titles
- `SRtng`, `RRtng`, `BRtng` - Standard, Rapid, Blitz ratings
- `Flag` - Status: empty=active, 'i'/'wi'=inactive

## Architecture

**fide_thinner.py**: Creates `fide_thin.sqlite` containing players who either:
1. Have any FIDE title (Tit, WTit, or OTit non-empty)
2. Are referenced in `players.sqlite` (via FideId → IdNumber)

Uses chunked reading (100K rows) for memory efficiency.

**fide_stats.py**: Outputs two reports to stdout:
1. Active/Inactive player counts by federation
2. Active/Inactive player counts by title (consolidates Tit > WTit > OTit priority)

## Data Files

- `data/fide.sqlite` - Source FIDE database (required)
- `data/players.sqlite` - Reference player IDs (required by fide_thinner.py)
- `data/fide_thin.sqlite` - Generated filtered output
