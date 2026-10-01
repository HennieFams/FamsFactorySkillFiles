#!/usr/bin/env python3
"""Mirror the historical-ticket exports (per-ticket JSON or CSV) from Azure Blob Storage to the VM.

Only blobs whose ETag changed since the last run are downloaded. If anything
changed, the search index is rebuilt automatically (unless --no-index).

Credentials (set ONE in the agent's env, via Paperclip secrets):
  AZURE_BLOB_CONTAINER_SAS_URL   https://<acct>.blob.core.windows.net/<container>?sv=...  (read+list SAS)
  AZURE_STORAGE_CONNECTION_STRING + AZURE_BLOB_CONTAINER
Optional:
  AZURE_BLOB_PREFIX              e.g. "freshdesk-export/"  (only blobs under this folder)

Usage:  python3 sync_blob.py [--no-index] [--force]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from common import RAW_DIR, HOME

STATE_FILE = HOME / "data" / "blob_state.json"


def container_client():
    from azure.storage.blob import ContainerClient

    sas = os.environ.get("AZURE_BLOB_CONTAINER_SAS_URL")
    if sas:
        return ContainerClient.from_container_url(sas)
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    name = os.environ.get("AZURE_BLOB_CONTAINER")
    if conn and name:
        return ContainerClient.from_connection_string(conn, name)
    sys.exit("No Blob credentials: set AZURE_BLOB_CONTAINER_SAS_URL or AZURE_STORAGE_CONNECTION_STRING + AZURE_BLOB_CONTAINER")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-index", action="store_true", help="do not rebuild the index afterwards")
    ap.add_argument("--force", action="store_true", help="re-download everything")
    args = ap.parse_args()

    prefix = os.environ.get("AZURE_BLOB_PREFIX") or None
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    state = {} if args.force or not STATE_FILE.exists() else json.loads(STATE_FILE.read_text())

    cc = container_client()
    changed = 0
    seen = set()
    for blob in cc.list_blobs(name_starts_with=prefix):
        if not blob.name.lower().endswith((".json", ".csv")):
            continue
        seen.add(blob.name)
        if state.get(blob.name) == blob.etag:
            continue
        rel = blob.name[len(prefix):] if prefix else blob.name
        dest = RAW_DIR / rel.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            cc.download_blob(blob.name).readinto(f)
        tmp.replace(dest)
        state[blob.name] = blob.etag
        changed += 1
        print(f"downloaded {blob.name} ({blob.size:,} bytes)")

    for gone in set(state) - seen:  # blob deleted upstream -> forget it (local copy kept)
        state.pop(gone)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(json.dumps({"export_blobs": len(seen), "downloaded": changed}))

    if changed and not args.no_index:
        subprocess.run([sys.executable, str(Path(__file__).with_name("build_index.py"))], check=True)


if __name__ == "__main__":
    main()
