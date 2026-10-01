---
name: similar-ticket-triage
description: Triage new Freshdesk tickets for the FAMS Support Agent — find similar resolved tickets in the historical ticket index, judge whether there is a strong, consistent known solution, and if so email a proposed answer to the internal reviewer. Use on every Support Agent run (webhook or manual).
---

# Similar-ticket triage

In the commands below `S=$SUPPORT_AGENT_HOME/scripts` and `PY=$SUPPORT_AGENT_HOME/.venv/bin/python`
(always use that Python — the system `python3` doesn't have the libraries). Work in a scratch dir:
`W=$(mktemp -d)`.

## 1. Work out which tickets to look at

1. If your Paperclip issue / trigger payload mentions a Freshdesk ticket id, put it first.
2. Also sweep for anything missed: call `get_tickets` (page 1, per_page 30). Keep tickets
   whose `created_at` is **after `$SUPPORT_AGENT_START_AT`** and within the last 7 days.
3. Drop ids the ledger already knows: `$PY $S/ledger.py unseen <id> <id> ...`
4. Skip (and `mark … skipped --note "<reason>"`) tickets that are:
   - from an internal requester (`@fams.co.za`, `@tecmo.co.za`) — tickets only carry a
     `requester_id`, so look the email up with `get_contact <requester_id>`;
   - outbound tickets started by our own agents (`source` = 10), e.g. sending login details;
   - spam, auto-replies, out-of-office, delivery-failure notices, or empty;
   - not a support question (e.g. sales enquiry, invoice request).
5. Process at most **5 tickets per run**, oldest first. The rest wait for the next run.

## 2. For each ticket

```bash
$PY $S/ledger.py claim <id>        # exit code 3 = someone else has it -> skip
```

**a. Read it.** `get_ticket <id>` and `get_ticket_conversation <id>`. Save the ticket JSON
(at least `id`, `subject`, `description_text`, `requester_id`, `company_id`) to `$W/<id>.json`.
Write down in one or two sentences what the customer's actual problem is (product area,
symptom, error text, unit/bowser/tank/store, site). Note the language — tickets come in
**Afrikaans or English**. The subject is often just the customer's company name, so the
problem is in the description. If a human agent has already replied, `mark … skipped`.

**b. Search history.**
```bash
$PY $S/search_similar.py --ticket-json $W/<id>.json --top 8
```
`same_customer_as_new: true` marks history from the same company/requester — it does not
count towards "other users". If results look thin, search again with your own rephrasing,
**in both languages** (e.g. "transaksies trek nie deur" and "transactions not syncing"):
`--description "<key symptoms>" --requester-id <id> --company-id <id> --exclude-id <id>`.
Optionally also check `list_solution_articles` / canned responses for an existing article.

**c. Judge — is there a sufficiently strong known solution?** Read every candidate's
description *and* resolution yourself; the scores are only a shortlist.

| Level | All of these must be true | Action |
|---|---|---|
| **HIGH** | ≥3 past tickets describe **the same problem**; they come from ≥2 **different customers** (`distinct_other_customers`, not the new ticket's customer); the agents' replies state **the same fix**; the fix is concrete (steps, setting, known cause — e.g. "OWW/Limesale bowsers must stay on battery long enough to send data") | email |
| **MEDIUM** | exactly 2 past tickets from 2 different customers with the same problem and the same concrete fix, **or** ≥3 that agree but one detail differs | email, flagged MEDIUM |
| **LOW / NONE** | anything weaker: similar words but different problem, fixes disagree, or the replies are only questions/acknowledgements ("Ons loer gou", "Op watter stoor…?", "Can we close the ticket?"), "fixed on our side", "tech sent to site", a quote/sales follow-up, or only the same customer had it before | **do nothing** |

Also choose **do nothing** when the answer depends on investigating this customer's own data
(missing transaction on a date, a specific balance/volume, a reconciliation figure) — those
need a human to look at the data, even if the topic is common.

**d. If LOW/NONE:**
```bash
$PY $S/ledger.py mark <id> no_match --confidence low --matched "<ids looked at>" --note "<why, 1 line>"
```

**e. If HIGH or MEDIUM — draft and send.** Write `$W/<id>.html` using the template below,
then:
```bash
$PY $S/send_email.py --to "$SUPPORT_REVIEWER_EMAIL" \
  --subject "[Support Agent] Ticket #<id> – <ticket subject> – <HIGH|MEDIUM> confidence" \
  --body-file $W/<id>.html --ticket-id <id>
$PY $S/ledger.py mark <id> sent --confidence <high|medium> --matched "<id1,id2,...>" --note "<fix in 1 line>"
```
If sending fails: `mark <id> error --note "<error>"` and report it in your issue comment.
Do not retry more than once in the same run.

## Email template (HTML, keep it plain)

```html
<p><b>Proposed answer for ticket <a href="https://{FRESHDESK_DOMAIN}/a/tickets/{id}">#{id}</a></b>
 — {subject}<br>Requester: {name} &lt;{email}&gt; · Region: {type} · Logged {created}<br>
 Confidence: <b>{HIGH|MEDIUM}</b> — based on {n} similar resolved tickets from {k} other customers.</p>

<p><b>Customer's problem (summary):</b> {1–2 sentences}</p>

<hr><p><b>Suggested reply to the customer</b> (ready to paste, review first):</p>
<div style="border-left:3px solid #ccc;padding-left:10px">
<p>Hi {first name},</p>
<p>{clear explanation + numbered steps, written for the customer, same language as their ticket.
   Only steps found in the past resolutions.}</p>
<p>Kind regards,<br>FAMS Support</p>
</div><hr>

<p><b>Why the agent thinks this fits:</b></p>
<ul>
  <li><a href="https://{FRESHDESK_DOMAIN}/a/tickets/{pastId}">#{pastId}</a> ({company}, {resolved date}) — {problem in a few words} → {fix in a few words}</li>
  …
</ul>
<p><b>Notes for the reviewer:</b> {differences from the past cases, anything to check first,
 internal action needed (e.g. reset on server side), or "none"}</p>
<p style="color:#888;font-size:12px">Generated automatically by the FAMS Support Agent. Nothing was sent to the customer.</p>
```

Write the suggested reply **in the ticket's language** and in the team's usual style
(e.g. "Hi Eva, Hoop dit gaan goed." / "Hi Kelly, Hope you are well."). Keep it short; no other
customers' names, company names or ticket numbers in the customer-facing part.
`internal_notes` from past tickets may go in *Notes for the reviewer*, never in the reply.
Never copy credentials (usernames, passwords, PINs) from history into an email.

## 3. Finish the run

Comment on your Paperclip issue, one line per ticket:
`#<id> <subject> → sent (HIGH, matched 812, 905, 1033)` / `→ no_match (fixes disagree)` / `→ skipped (internal)`.
Then mark the issue done.

## Housekeeping

- If `search_similar.py` errors with "no such table", the index is missing:
  run `$PY $S/sync_blob.py` (downloads the exports and rebuilds), then retry.
- Stale claim from a crashed run (>1 hour old, no outcome): `$PY $S/ledger.py release <id>`.
