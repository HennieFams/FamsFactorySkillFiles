#!/usr/bin/env bash
# Offline smoke test: index the synthetic tickets, search, ledger, dry-run email.  bash tests/smoke_test.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export SUPPORT_AGENT_HOME=$(mktemp -d) SUPPORT_AGENT_CONFIG=$ROOT/config
mkdir -p $SUPPORT_AGENT_HOME/data/raw && cp -r $ROOT/tests/sample_raw/* $SUPPORT_AGENT_HOME/data/raw/
S=$ROOT/scripts
python3 $S/build_index.py
python3 $S/search_similar.py --ticket-json $ROOT/tests/new_ticket.json --top 5 > $SUPPORT_AGENT_HOME/res.json
python3 - "$SUPPORT_AGENT_HOME/res.json" <<'PY'
import json,sys; d=json.load(open(sys.argv[1])); c=d["resolution_clusters"][0]
print("top cluster:", c); assert c["distinct_other_customers"]>=3, "expected the 3 bowser tickets to cluster"
assert all(x["ticket_id"]!="9005" for x in d["candidates"]), "outbound ticket must not be indexed"
PY
python3 $S/ledger.py claim 9100 && python3 $S/ledger.py mark 9100 sent --confidence high --matched 9001,9002,9003
echo "<p>test</p>" > $SUPPORT_AGENT_HOME/b.html
export SUPPORT_EMAIL_ALLOWED_TO=schalk@fams.co.za SUPPORT_EMAIL_MODE=dryrun
python3 $S/send_email.py --to schalk@fams.co.za --subject test --body-file $SUPPORT_AGENT_HOME/b.html --ticket-id 9100
if python3 $S/send_email.py --to someone@customer.co.za --subject t --body-file $SUPPORT_AGENT_HOME/b.html --ticket-id 9100 2>/dev/null; then
  echo "FAIL: non-allow-listed address accepted"; exit 1; fi
echo "SMOKE TEST PASSED"
