#!/usr/bin/env python3
"""Send the proposed answer to the internal reviewer — and ONLY to allow-listed addresses.

This is the agent's only way to send email. It refuses any recipient not in
SUPPORT_EMAIL_ALLOWED_TO, so a bad prompt or a confused run can never email a customer.

Env (via Paperclip secrets):
  SUPPORT_EMAIL_MODE        fams_proxy | graph | smtp | dryrun   (default: dryrun)
  SUPPORT_EMAIL_ALLOWED_TO  comma list, e.g. schalk@fams.co.za
  -- fams_proxy mode (FAMS's existing SendGrid proxy - the one already bound to a sender) --
  SENDGRID_PROXY_BASE       required, e.g. https://<your-api-host>/api/SendGrid  (keep it out of git)
                            POST {base}/SendMessageEmail  {"email", "subject", "body"}  (one call per recipient)
  -- graph mode (Microsoft 365) --
  SUPPORT_EMAIL_FROM        sending mailbox, e.g. support-agent@fams.co.za
  GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET   (app registration with Mail.Send application permission)
  -- smtp mode --
  SMTP_HOST (smtp.office365.com), SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD

Usage:
  python3 send_email.py --to schalk@fams.co.za --subject "..." --body-file draft.html --ticket-id 1234
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from common import OUTBOX


def allowed():
    return {a.strip().lower() for a in os.environ.get("SUPPORT_EMAIL_ALLOWED_TO", "").split(",") if a.strip()}


def send_graph(sender, to, subject, html_body):
    import requests

    tenant = os.environ["GRAPH_TENANT_ID"]
    tok = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "client_id": os.environ["GRAPH_CLIENT_ID"],
            "client_secret": os.environ["GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    tok.raise_for_status()
    r = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
        headers={"Authorization": f"Bearer {tok.json()['access_token']}"},
        json={
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": a}} for a in to],
            },
            "saveToSentItems": True,
        },
        timeout=30,
    )
    if r.status_code != 202:
        raise RuntimeError(f"Graph sendMail failed {r.status_code}: {r.text[:500]}")


def send_fams_proxy(to, subject, html_body):
    """Same contract as shared/email.py send_email(): flat JSON, sender is fixed on the API side."""
    import requests

    base = os.environ.get("SENDGRID_PROXY_BASE", "").rstrip("/")
    if not base:
        raise RuntimeError("SENDGRID_PROXY_BASE is not set")
    for addr in to:
        r = requests.post(f"{base}/SendMessageEmail",
                          json={"email": addr, "subject": subject, "body": html_body}, timeout=30)
        if r.status_code not in (200, 201, 202):
            raise RuntimeError(f"SendGrid proxy failed for {addr}: {r.status_code} {r.text[:300]}")


def send_smtp(sender, to, subject, html_body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, ", ".join(to), subject
    msg.set_content("This message is HTML. Open it in an HTML-capable mail client.")
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.office365.com"), int(os.environ.get("SMTP_PORT", "587")), timeout=30) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="comma-separated; every address must be allow-listed")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body-file", required=True, help="HTML file with the email body")
    ap.add_argument("--ticket-id", required=True)
    a = ap.parse_args()

    to = [x.strip().lower() for x in a.to.split(",") if x.strip()]
    ok = allowed()
    if not ok:
        sys.exit("REFUSED: SUPPORT_EMAIL_ALLOWED_TO is empty")
    bad = [x for x in to if x not in ok]
    if bad or not to:
        sys.exit(f"REFUSED: recipient(s) not allow-listed: {bad or '(none)'}. Allowed: {sorted(ok)}")

    body = Path(a.body_file).read_text(encoding="utf-8")
    mode = os.environ.get("SUPPORT_EMAIL_MODE", "dryrun").lower()
    sender = os.environ.get("SUPPORT_EMAIL_FROM", "support-agent@fams.co.za")

    OUTBOX.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (OUTBOX / f"{stamp}_ticket{a.ticket_id}.html").write_text(
        f"<!-- mode={mode} from={sender} to={','.join(to)} subject={a.subject} -->\n{body}", encoding="utf-8")

    if mode == "fams_proxy":
        send_fams_proxy(to, a.subject, body)
    elif mode == "graph":
        send_graph(sender, to, a.subject, body)
    elif mode == "smtp":
        send_smtp(sender, to, a.subject, body)
    elif mode != "dryrun":
        sys.exit(f"Unknown SUPPORT_EMAIL_MODE={mode}")
    print(json.dumps({"sent": mode != "dryrun", "mode": mode, "to": to, "ticket_id": a.ticket_id}))


if __name__ == "__main__":
    main()
