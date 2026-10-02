"""
Run ONE read-only SQL statement against FAMS and print / export the result.

Read-only, always. Every statement goes through fams_db.assert_read_only()
and runs inside a transaction that is rolled back. There is deliberately
no way to run UPDATE/DELETE through this tool: when an investigation ends
in a data fix, hand the human the exact SQL (preview SELECT + explicit ID
list + the write) to run themselves in SSMS. See FAMS_INTEGRITY/CLAUDE.md.

Placeholders:
  {Name}  - filled from --param Name=VALUE and sent as a bound parameter
            (the placeholder is replaced by ?, so values are never pasted
            into the SQL text). Write '{StartDate}' or {StartDate} - quotes
            around a placeholder are removed automatically.

Examples:
    python run_query.py --sql "SELECT TOP 5 * FROM Account WHERE name LIKE {Term}" --param Term=%Ship%
    python run_query.py --sql-file q.sql --param AccountID=373 --param StartDate=2026-09-01 --csv out.csv
    python run_query.py --proc --sql "EXEC get_ReportinglogbookRev6SARS @account = {AccountID}, @from = {From}, @to = {To}" \
        --param AccountID=278 --param From=2025-10-01 --param To=2025-11-01
"""
import argparse
import csv
import re
import sys

from fams_db import ReadOnlyViolation, query

_PLACEHOLDER = re.compile(r"'?\{([A-Za-z_][A-Za-z0-9_]*)\}'?")


def bind(sql, raw_params):
    values = {}
    for p in raw_params or []:
        k, _, v = p.partition("=")
        values[k] = v
    ordered = []

    def repl(m):
        name = m.group(1)
        if name not in values:
            sys.exit(f"Missing --param {name}=...")
        ordered.append(values[name])
        return "?"

    return _PLACEHOLDER.sub(repl, sql), ordered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql")
    ap.add_argument("--sql-file")
    ap.add_argument("--param", action="append", help="Name=VALUE, repeatable")
    ap.add_argument("--csv", help="Write all rows to this CSV")
    ap.add_argument("--limit", type=int, default=500, help="Max rows to print")
    ap.add_argument("--proc", action="store_true",
                    help="Allow EXEC of an allowlisted read-only report proc (fams_db.ALLOWED_PROCS)")
    args = ap.parse_args()

    if args.sql:
        sql = args.sql
    elif args.sql_file:
        with open(args.sql_file) as f:
            sql = f.read()
    else:
        sys.exit("Provide --sql or --sql-file")

    sql, params = bind(sql, args.param)
    try:
        cols, rows = query(sql, params, allow_procs=args.proc)
    except ReadOnlyViolation as e:
        sys.exit(f"REFUSED (read-only guard): {e}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        print(f"Wrote {len(rows)} rows to {args.csv}")
    print("\t".join(cols))
    for r in rows[: args.limit]:
        print("\t".join("" if v is None else str(v) for v in r))
    if len(rows) > args.limit:
        print(f"... ({len(rows) - args.limit} more rows, use --csv to export all)")
    print(f"\n{len(rows)} row(s) total")


if __name__ == "__main__":
    main()
