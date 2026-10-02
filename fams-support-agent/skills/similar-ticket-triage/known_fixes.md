# FAMS Support — Known fixes playbook

Recurring problems with a **consistent, concrete fix** across several customers. Built from the
history research (TEC-44, Oct 2026) — **Schalk to review and correct wording**; once he has, change
`Reviewed:` to his name and date. Add new entries the same way (≥3 tickets, ≥2 customers, same fix).

How the agent uses this file (see SKILL.md step c):
- A new ticket must clearly be the **same problem** as an entry (match the "Recognise it by" list,
  and none of the "Not this entry if" points).
- Still run `search_similar.py` and list any matching past tickets as evidence, but a clear playbook
  match is enough for **HIGH** on its own (the fix was already proven across customers).
- Write the customer reply from the "Reply should say" points, in the ticket's language. Don't add
  steps that aren't here or in the matched history.

Reviewed: not yet

---

## K1 — Forgot password / needs login details
**Recognise it by:** "forgot password", "wagwoord vergeet", "can't log in", "login details",
"username", "password reset", new staff member asking for portal login.
**Not this entry if:** the user *can* log in but sees wrong/missing data; the portal itself is down
for everyone; it's a request to create a brand-new user with specific rights (needs a human).
**Fix (internal):** support looks up the account in FAMS admin and resets the password if needed,
then sends username + password.
**Reply should say:** here are your login details — `Username: [ ]`, `Password: [ ]` — and the
portal link; ask them to change the password after logging in if that option exists.
**Special rule:** NEVER put a real or old username/password in the email — always the blank
`[ ]` placeholders. Reviewer note must say: "Reset/look up in FAMS admin and fill in before sending."
**Evidence:** #1665, #1869, #1400, #1818, #2632, #3001, #3270, #3713, #3721, #382

## K2 — Tag "invalid" / not working after a tag or vehicle-registration change (DWN)
**Recognise it by:** "invalid tag", "tag werk nie", new/replaced tag not working, vehicle
registration changed and now tag/vehicle not accepted, "DWN", recently added driver/vehicle tag
rejected at the pump.
**Not this entry if:** a tag that *always* worked suddenly stopped with no change made (could be a
damaged tag/reader — needs a human); the whole unit is offline; the customer says it was already
downloaded and synced and still fails (then a human must check scan order/record).
**Fix:** edit the record in the portal and set it to download (DWN). The change only becomes active
once the unit is online and has synced — orange/"DWN" = pending, grey = done. Loadshedding or poor
signal can delay this. If still invalid after the download completed, check the scan order
(equipment tag before driver/operator tag).
**Reply should say:** (1) make sure the record is set to download (DWN) and saved; (2) wait for the
unit to come online and sync — status turns from orange to grey; (3) if it still says invalid after
that, check the scan order (equipment/vehicle tag first, then driver tag) and let us know.
**Evidence:** #1129, #1545, #2043, #805, #2380, #2724, #3147, #3471, #3540, #2444, #4946

## K3 — Mobile/handheld bowser unit not sending data / "can't connect to unit"
**Recognise it by:** mobile or handheld bowser unit not uploading, transactions not pulling through
from a mobile/bowser unit, "can't connect to the unit", unit screen dark/off.
**Not this entry if:** a fixed site/tank unit (not mobile); the unit is on and charged but still not
sending (network/hardware — needs a human); data missing for specific dates the customer wants
investigated (account-specific).
**Fix:** battery flat or unit switched off — put it on its charger and switch it on; it needs several
hours to charge fully and connects/uploads by itself once powered with signal. (OWW/Limesale bowsers:
must stay powered long enough after a transaction to send the data.)
**Reply should say:** put the unit on charge and switch it on; leave it on (with signal) for a few
hours so it can charge and send its data; transactions should then appear on the portal; if they
still don't after that, let us know the unit name.
**Evidence:** #816, #913, #1398, #1591, #1616 (also #4942/#4944 — same customer, not counted)

## K4 — Wireless tank-level / dip sensor shows no reading or stale level
**Recognise it by:** tank level not updating, "no reading", "stale level", "tenkvlak wys nie",
wireless/solar dip sensor offline.
**Not this entry if:** the level is updating but wrong (calibration — needs a human); the whole site
unit is offline (not just the tank sensor).
**Fix:** the wireless sensor's own battery is low/dead (solar ones too) — replace or recharge the
sensor battery; readings resume once powered.
**Reply should say:** the tank sensor's battery is most likely flat; please check/charge or replace
the sensor battery (for solar sensors, check the panel is clean and in sun); readings should come
back by themselves once it has power; tell us if it doesn't.
**Evidence:** #3082, #3390, #295, #1593

## K5 — Scheduled report emails stopped arriving
**Recognise it by:** "scheduled report not received", "monthly/daily report didn't arrive",
"verslag nie ontvang".
**Not this entry if:** the report arrives but the figures are wrong; they want a new report set up.
**Fix:** check spam/junk first (mail-side filtering FAMS can't control); confirm the recipient is
still on the report's mailing list.
**Reply should say:** please check your spam/junk folder and mark FAMS mail as safe; we'll confirm
your address is still on the report's recipient list. (Reviewer: check the recipient list before
sending.)
**Evidence:** #2498, #3025, #735
