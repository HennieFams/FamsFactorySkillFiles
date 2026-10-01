"""Shared paths, config loading and text helpers for the FAMS Support Agent scripts."""
import html
import json
import os
import re
from pathlib import Path

HOME = Path(os.environ.get("SUPPORT_AGENT_HOME", "/paperclip/fams-support-agent"))
RAW_DIR = HOME / "data" / "raw"          # CSVs mirrored from Azure Blob
INDEX_DB = HOME / "data" / "history.db"  # SQLite + FTS5 index of past tickets
LEDGER_DB = HOME / "data" / "ledger.db"  # which new tickets were already handled
OUTBOX = HOME / "data" / "outbox"        # copy of every email sent / dry-run
CONFIG_DIR = Path(os.environ.get("SUPPORT_AGENT_CONFIG", HOME / "config"))
ENV_FILE = HOME / "config" / "agent.env"  # secrets + settings, chmod 600, never in git


def _load_env_file(path: Path = ENV_FILE) -> None:
    """KEY=value lines -> os.environ (values already set in the environment win)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, PermissionError):
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        os.environ.setdefault(k.strip(), v)


_load_env_file()


def load_column_map() -> dict:
    with open(CONFIG_DIR / "column_map.json", encoding="utf-8") as f:
        return json.load(f)


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# Lines that usually start quoted history / signatures in email replies
_CUT_RE = re.compile(
    r"(^|\n)\s*(On .{5,80} wrote:|-----Original Message-----|From: .{3,200}?Sent: |Kind regards|Best regards|Regards,"
    r"|Groete\b|Vriendelike groete|Ticket: https?://\S+/helpdesk/tickets/\d+)",
    re.IGNORECASE,
)


def clean_text(value, cut_quoted: bool = False) -> str:
    if value is None:
        return ""
    s = str(value)
    s = re.sub(r"<br\s*/?>|</p>|</div>", "\n", s, flags=re.IGNORECASE)
    s = _TAG_RE.sub(" ", s)
    s = html.unescape(s)
    if cut_quoted:
        m = _CUT_RE.search(s)
        if m and m.start() > 15:
            s = s[: m.start()]
    s = _TICKET_LINK_RE.sub(" ", s)
    s = redact(s)
    lines = [_WS_RE.sub(" ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


_TICKET_LINK_RE = re.compile(r"Ticket: https?://\S+/helpdesk/tickets/\d+", re.IGNORECASE)
_SECRET_RE = re.compile(r"(?i)\b(password|passwd|pwd|wagwoord|pin)\s*[:=]\s*\S+")


def redact(s: str) -> str:
    """Remove obvious credentials (e.g. 'Password: Amy4321!') before anything is indexed or emailed."""
    return _SECRET_RE.sub(lambda m: m.group(1) + ": [REDACTED]", s)


def none_if_null(v):
    """Exports store nulls/booleans as strings ('None', 'False')."""
    return None if v is None or str(v).strip() in {"", "None", "null"} else v


def truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


STOPWORDS = set(
    """a an and are as at be been but by can could do does for from had has have hello hi how i if in
    is it its me my no not of on or our please regards so thanks thank that the their them then there
    these they this to us was we were what when where which who why will with would you your dear kind
    best team issue problem help ticket urgent asap good morning afternoon also just still get got
    kindly advise assist day trust well hope regards attached see find kindly feedback
    die en van het is nie ek ons dit wat op vir met aan te na om sal kan jy julle asb asseblief baie
    dankie goeie more middag dag groete hoop gaan goed daar ook maar wil net as of by sy hy word hulle
    kyk gou laat weet gerus enige iets anders soos sien hier hierdie toe reg mag moet dat al nog
    """.split()
)
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]{1,}")


def keywords(text: str, limit: int = 25) -> list:
    """Distinct, lower-cased content words in order of first appearance."""
    seen, out = set(), []
    for w in _WORD_RE.findall(text.lower()):
        w = w.strip("-_")
        if len(w) < 3 or w in STOPWORDS or w.isdigit() and len(w) < 4:
            continue
        if w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= limit:
            break
    return out
