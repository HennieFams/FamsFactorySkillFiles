"""
FAMS DB connection check (thin wrapper over fams_db.py).

All connection logic, credential handling and the read-only guard live in
fams_db.py - see its docstring for the env-var contract (FAMS_DB_* for the
Paperclip agent, FAMS_SQL_* for local use) and the three read-only layers.

Usage:
    python db_connect.py --test
"""
import argparse
import sys

from fams_db import test_connection

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="Verify the connection works")
    args = ap.parse_args()
    if args.test:
        try:
            print("Connection OK:", test_connection())
        except Exception as e:
            sys.exit(f"Connection FAILED: {e}")
    else:
        ap.print_help()
