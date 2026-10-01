# Freshdesk automation rule — "Wake FAMS Support Agent"

Freshdesk Admin → **Workflows → Automations → Ticket Creation** tab → **New rule**

| Field | Value |
|---|---|
| Rule name | Wake FAMS Support Agent |
| When a ticket is created | (leave "Ticket is created") |
| Conditions | **Match ANY**: `Source` is `Email`, `Portal`, `Phone`, `Chat`, `Feedback widget` (i.e. leave out anything you don't want triaged). Optional extra condition: `Requester email` does not contain `@fams.co.za` |
| Action | **Trigger webhook** |
| Request type | `POST` |
| URL | the `webhookUrl` Paperclip showed when you created the webhook trigger, with your public host in front, e.g. `https://famsfactory-vm.southafricanorth.cloudapp.azure.com/api/routine-triggers/public/<publicId>/fire` |
| Requires authentication | No (we use a custom header instead) |
| Custom headers | `Authorization: Bearer <webhookSecret from Paperclip>` |
| Encoding | JSON |
| Content | **Advanced** → paste the body below |

```json
{
  "source": "freshdesk",
  "event": "ticket_created",
  "ticket_id": "{{ticket.id}}",
  "subject": "{{ticket.subject}}",
  "requester_email": "{{ticket.requester.email}}"
}
```

Save and move the rule to the top of the Ticket Creation list (rules run in order; a rule
above it with "stop processing" would prevent the webhook).

**Test:** log a ticket from a non-FAMS mailbox, then check
Paperclip → Routines → "Triage new Freshdesk tickets" → Runs. A run should appear within
seconds. If not, check `/var/log/caddy/webhook.log` on the VM and the Freshdesk rule's
webhook log.

Notes
- The description is deliberately not sent in the payload; the agent reads the full ticket
  through the Freshdesk MCP, so nothing sensitive sits in Paperclip trigger logs.
- If the webhook ever fails, the hourly safety-net schedule picks the ticket up anyway
  (the ledger stops it being handled twice).
