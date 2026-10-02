"""
fams_db.py - the ONLY way FAMS integrity tooling talks to the FAMS database.

Why this file exists
--------------------
The SQL login the integrity agent uses has full admin rights, and a
dedicated read-only login could not be created. So read-only behaviour is
enforced here, in three independent layers. Every query - from the daily
check engine, from run_query.py, from an ad hoc investigation - must go
through `query()` / `query_df()`. Never open your own connection.

  Layer 1 - static guard (`assert_read_only`)
      The statement is lexed (comments, string literals and quoted
      identifiers removed first, so `-- DELETE` or `'UPDATE'` or [Insert]
      cannot fool it, and a real DELETE cannot hide behind a comment). It
      must be a single statement starting with SELECT or WITH, and must not
      contain any write / DDL / side-effect keyword (incl. SELECT ... INTO,
      EXEC, NEXT VALUE FOR, OPENROWSET, WAITFOR, xp_/sp_ calls, Service
      Broker / cursor verbs that could start a second statement without ';',
      and schema-qualified function calls, which could be CLR code with
      side effects). Control characters are rejected outright, and a -- comment
      ends at CR as well as LF, as it does in SQL Server.
      The one exception is an explicit allowlist of read-only reporting
      stored procedures (ALLOWED_PROCS), which must be called in the exact
      form `EXEC <proc> @a = ?, @b = ?` and only when the caller passes
      allow_procs=True.

  Layer 2 - always-rollback transaction
      Autocommit is off. Every statement runs inside a transaction that is
      ROLLED BACK after the rows are fetched - success or failure. Anything
      that slipped past layer 1 and wrote data is undone.

  Layer 3 - read-only connection intent
      pyodbc connections declare ApplicationIntent=ReadOnly, so if the
      Azure SQL tier has a readable secondary the session is routed there
      (where writes are physically impossible). On tiers without one this
      is a harmless no-op.

Credentials (environment variables only - never hardcode, never print):
  Paperclip agent:  FAMS_DB_HostName, FAMS_DB_DBName, FAMS_DB_UserName, FAMS_DB_Password
  Local / analyst:  FAMS_SQL_SERVER, FAMS_SQL_DATABASE, FAMS_SQL_USER, FAMS_SQL_PASSWORD
                    (or FAMS_SQL_CONN_STR, a full ODBC connection string)
  The FAMS_DB_* set wins when both are present.

Driver: FAMS_DB_DRIVER = auto (default) | pyodbc | pymssql
  auto uses pyodbc when "ODBC Driver 18 for SQL Server" is installed,
  otherwise pymssql (pure pip wheel: `pip install pymssql`).

Lives in fams-integrity-agent/scripts/ (installed on the Paperclip VM at
/paperclip/fams-integrity-agent/scripts/). Skill folders carry no code - the
Paperclip skill importer rejects skills that contain executable scripts.
"""
from __future__ import annotations

import os
import re

DEFAULT_SERVER = "db.fams.co.za"
DEFAULT_DATABASE = "FAMS2018"
QUERY_TIMEOUT_SECONDS = 300

# Read-only reporting procedures that may be EXECuted (allow_procs=True only).
ALLOWED_PROCS = {"get_reportinglogbookrev6sars"}

FORBIDDEN_KEYWORDS = {
    # DML / DDL / DCL
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "ALTER", "DROP", "TRUNCATE",
    "CREATE", "GRANT", "DENY", "REVOKE", "RENAME",
    # SELECT ... INTO creates/fills a table
    "INTO",
    # procedure / dynamic SQL execution
    "EXEC", "EXECUTE", "SP_EXECUTESQL",
    # external data / bulk / server-level side effects
    "OPENROWSET", "OPENQUERY", "OPENDATASOURCE", "BULK", "BACKUP", "RESTORE",
    "DBCC", "KILL", "SHUTDOWN", "RECONFIGURE", "CHECKPOINT", "WAITFOR",
    # batch / session / transaction control (only fams_db issues these)
    "USE", "SET", "DECLARE", "BEGIN", "COMMIT", "ROLLBACK", "SAVE", "GO",
    "ENABLE", "DISABLE",
    # legacy text-pointer writes, flow control
    "WRITETEXT", "UPDATETEXT", "READTEXT", "GOTO", "RAISERROR", "THROW", "PRINT",
    # statements that can start a second batch statement without ';'
    "RECEIVE", "SEND", "CONVERSATION", "DIALOG", "SETUSER", "REVERT", "OPEN", "CLOSE", "DEALLOCATE",
}

# Raw characters that are never needed in a query but that SQL Server may treat as
# line breaks (ending a -- comment early) - reject outright rather than guess.
_BAD_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x85\u2028\u2029]")
# schema-qualified function call, e.g. dbo.fn(...) / [dbo].[fn](...): user code
# (possibly CLR with external side effects) - not allowed in a guarded query
_QUALIFIED_CALL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\.\s*[A-Za-z_][A-Za-z0-9_]*\s*\(")


class ReadOnlyViolation(Exception):
    """Raised when a statement is not provably read-only. Never retried."""


# --------------------------------------------------------------------------
# Lexer: blank out comments and literals so keyword checks see only code
# --------------------------------------------------------------------------
def _sanitize(sql: str) -> str:
    """Return `sql` with comments removed, string literals replaced by '?',
    and quoted identifiers ([x] / "x") replaced by the bare word IDENT.
    Raises ReadOnlyViolation on any unterminated comment/literal."""
    out = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if c == "-" and nxt == "-":  # line comment - ends at CR or LF (SQL Server honours both)
            m = re.compile(r"[\r\n]").search(sql, i)
            i = n if m is None else m.start()
            out.append(" ")
        elif c == "/" and nxt == "*":  # block comment (T-SQL allows nesting)
            depth, i = 1, i + 2
            while i < n and depth:
                if sql.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif sql.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            if depth:
                raise ReadOnlyViolation("Unterminated block comment")
            out.append(" ")
        elif c == "'" or (c in "Nn" and nxt == "'" and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == "_"))):
            i += 2 if c in "Nn" else 1
            while True:
                if i >= n:
                    raise ReadOnlyViolation("Unterminated string literal")
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append("'?'")
        elif c in "[\"":
            close = "]" if c == "[" else '"'
            i += 1
            while True:
                if i >= n:
                    raise ReadOnlyViolation("Unterminated quoted identifier")
                if sql[i] == close:
                    if i + 1 < n and sql[i + 1] == close:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append(" IDENT ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


_WORD = re.compile(r"[A-Za-z_@#][A-Za-z0-9_@#$]*")
_PROC_CALL = re.compile(
    r"^EXEC(?:UTE)?\s+(?:dbo\s*\.\s*)?([A-Za-z_][A-Za-z0-9_]*)"
    r"((?:\s+@[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:\?|'\?'|-?\d+(?:\.\d+)?)\s*,?)*)\s*$",
    re.IGNORECASE,
)


def assert_read_only(sql: str, allow_procs: bool = False) -> None:
    """Raise ReadOnlyViolation unless `sql` is a single read-only statement."""
    if not isinstance(sql, str) or not sql.strip():
        raise ReadOnlyViolation("Empty statement")
    if _BAD_CHARS.search(sql):
        raise ReadOnlyViolation("Control/line-separator characters are not allowed in a query")
    clean = _sanitize(sql).strip()
    if clean.endswith(";"):
        clean = clean[:-1].rstrip()
    if ";" in clean:
        raise ReadOnlyViolation("Multiple statements are not allowed (found ';')")
    words = [w.upper() for w in _WORD.findall(clean)]
    if not words:
        raise ReadOnlyViolation("No SQL keywords found")

    if words[0] in ("EXEC", "EXECUTE"):
        m = _PROC_CALL.match(clean)
        if allow_procs and m and m.group(1).lower() in ALLOWED_PROCS:
            return
        raise ReadOnlyViolation(
            "EXEC is only allowed for allowlisted read-only report procedures "
            f"{sorted(ALLOWED_PROCS)} with allow_procs=True, in the form "
            "`EXEC <proc> @param = ?, ...`"
        )

    if words[0] not in ("SELECT", "WITH"):
        raise ReadOnlyViolation(f"Statement must start with SELECT or WITH, not {words[0]}")
    bad = sorted({w for w in words if w in FORBIDDEN_KEYWORDS})
    if bad:
        raise ReadOnlyViolation(f"Forbidden keyword(s) in read-only query: {', '.join(bad)}")
    if _QUALIFIED_CALL.search(clean):
        raise ReadOnlyViolation("Schema-qualified function calls (user/CLR code) are not allowed")
    sys_procs = sorted({w for w in words if w.startswith(("XP_", "SP_"))})
    if sys_procs:
        raise ReadOnlyViolation(f"System procedure reference not allowed: {', '.join(sys_procs)}")
    for a, b, c in zip(words, words[1:], words[2:]):
        if (a, b, c) == ("NEXT", "VALUE", "FOR"):
            raise ReadOnlyViolation("NEXT VALUE FOR advances a sequence (a write)")


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------
def _settings() -> dict:
    env = os.environ
    if env.get("FAMS_DB_UserName") or env.get("FAMS_DB_Password"):
        s = {
            "server": env.get("FAMS_DB_HostName") or DEFAULT_SERVER,
            "database": env.get("FAMS_DB_DBName") or DEFAULT_DATABASE,
            "user": env.get("FAMS_DB_UserName"),
            "password": env.get("FAMS_DB_Password"),
            "conn_str": None,
        }
    else:
        s = {
            "server": env.get("FAMS_SQL_SERVER") or DEFAULT_SERVER,
            "database": env.get("FAMS_SQL_DATABASE") or DEFAULT_DATABASE,
            "user": env.get("FAMS_SQL_USER"),
            "password": env.get("FAMS_SQL_PASSWORD"),
            "conn_str": env.get("FAMS_SQL_CONN_STR"),
        }
    if not s["conn_str"] and not (s["user"] and s["password"]):
        raise RuntimeError(
            "No FAMS DB credentials in the environment. Set FAMS_DB_UserName/FAMS_DB_Password "
            "(Paperclip) or FAMS_SQL_USER/FAMS_SQL_PASSWORD (local), or FAMS_SQL_CONN_STR. "
            "Never paste credentials into chat."
        )
    return s


def _driver() -> str:
    choice = os.environ.get("FAMS_DB_DRIVER", "auto").lower()
    if choice in ("pyodbc", "pymssql"):
        return choice
    try:
        import pyodbc  # noqa: F401
        if any("ODBC Driver 18 for SQL Server" in d for d in pyodbc.drivers()):
            return "pyodbc"
    except ImportError:
        pass
    try:
        import pymssql  # noqa: F401
        return "pymssql"
    except ImportError:
        raise RuntimeError(
            "No SQL Server driver available. Install one of:\n"
            "  pip install pymssql            (no OS dependencies)\n"
            "  pip install pyodbc  + 'ODBC Driver 18 for SQL Server'"
        )


def _scrub(msg: str, s: dict) -> str:
    for secret in (s.get("password"), s.get("conn_str"), s.get("user")):
        if secret:
            msg = msg.replace(secret, "***")
    return msg


def _connect():
    s = _settings()
    drv = _driver()
    try:
        if drv == "pyodbc":
            import pyodbc
            cs = s["conn_str"] or (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER=tcp:{s['server']},1433;DATABASE={s['database']};"
                f"UID={s['user']};PWD={s['password']};"
                "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            )
            if "applicationintent" not in cs.lower():
                cs = cs.rstrip(";") + ";ApplicationIntent=ReadOnly;"
            conn = pyodbc.connect(cs, autocommit=False)
            conn.timeout = QUERY_TIMEOUT_SECONDS
        else:
            import pymssql
            if s["conn_str"]:
                raise RuntimeError("FAMS_SQL_CONN_STR needs pyodbc; set the individual vars for pymssql")
            conn = pymssql.connect(server=s["server"], user=s["user"], password=s["password"],
                                   database=s["database"], login_timeout=30,
                                   timeout=QUERY_TIMEOUT_SECONDS, autocommit=False)
        return conn, drv
    except Exception as e:  # never leak credentials through an exception message
        raise RuntimeError(f"FAMS DB connection failed ({drv}): {_scrub(str(e), s)}") from None


def _to_pyformat(sql: str) -> str:
    """pymssql uses %s placeholders and %-formats the whole string."""
    out, i, n, in_str = [], 0, len(sql), False
    while i < n:
        c = sql[i]
        if c == "%":
            out.append("%%")
        elif c == "'":
            in_str = not in_str
            out.append(c)
        elif c == "?" and not in_str:
            out.append("%s")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def query(sql: str, params=None, allow_procs: bool = False):
    """Run one read-only statement. Returns (columns, rows). Always rolls back."""
    assert_read_only(sql, allow_procs=allow_procs)
    params = tuple(params or ())
    conn, drv = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 30000;")
        if drv == "pymssql":
            cur.execute(_to_pyformat(sql), params if params else None)
        else:
            cur.execute(sql, params)
        # a proc can return several result sets; keep the last one with columns
        cols, rows = [], []
        while True:
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = [tuple(r) for r in cur.fetchall()]
            try:
                more = cur.nextset()
            except Exception:
                more = False
            if not more:
                break
        return cols, rows
    finally:
        try:
            conn.rollback()  # layer 2: nothing this session did survives
        finally:
            conn.close()


def query_df(sql: str, params=None, allow_procs: bool = False):
    """Same as query() but returns a pandas DataFrame."""
    import pandas as pd
    cols, rows = query(sql, params, allow_procs=allow_procs)
    return pd.DataFrame.from_records(rows, columns=cols)


def test_connection() -> str:
    _, rows = query("SELECT @@VERSION")
    return str(rows[0][0])[:80]
