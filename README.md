# Do Nothing Time Tracker

A Flet-built desktop/web app for tracking work sessions, projecting expected hours, and comparing against monthly and year-to-date goals.

https://www.youtube.com/watch?v=8An2SxNFvmU

## Features
- One-click clock in/out with automatic prevention of overlapping entries.
- Live "worked time" indicator for the selected day, refreshing every minute.
- Absence manage with multiple-day absences.
- week/month/year level stats: expected hours (based on config + absences), actual totals, and deltas.
- Complete history browser grouped by week, with inline edit/delete/new entry actions.
- JSON persistence

## Project structure
```
config.json                # Workday configuration (hours per day, workdays, etc.)
data/entries/              # Automatically created monthly JSON files
data/absences/             # Per-year JSON files with credited absences
do_nothing_time_tracker/   # Python package with app logic & UI
main.py                    # Entry point executed by Flet
```

## Getting started
1. Create a Python 3.10+ virtual environment.
2. Install the package in editable mode (pulls in dependencies automatically):
   ```bash
   pip install -e .
   ```
4. Launch the UI via the installed console script:
   ```bash
   dntt
   ```

Monthly entry files are written to `data/entries/<year>-<month>.json`. Delete or edit them manually if you need to reset data.

## Importing Factorial XLSX exports
If you want to import your current Factorial entries, export a complete version in hh:mm format in xlsx and import it with:

```bash
dntt-import path/to/export.xlsx \
  --output-dir data/entries \
  --absences-dir data/absences 
```

