"""Offline tests for the Notion client-portal publisher (no network)."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)

import publish_notion as pn  # noqa: E402
import test_engine as te  # noqa: E402

DS = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    doc, out = te.result.__wrapped__(tmp_path_factory)
    cfg = te.base_cfg()
    cfg["notion"]["sites"] = {str(te.ACC): {"site": "Test - Depot", "data_source_id": DS}}
    return doc, str(out), cfg


class FakeNotion(pn.NotionClient):
    def __init__(self, existing=None):
        super().__init__("tok", "2025-09-03", [DS])
        self.existing = existing or {}
        self.calls = []

    def _call(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path.endswith("/query"):
            f = body["filter"]["date"]
            if "equals" in f:
                return {"results": self.existing.get(f["equals"], [])}
            return {"results": [{"properties": {"Date": {"date": {"start": "2026-09-29"}},
                                                "Usage %": {"number": 97.5}, "ATG %": {"number": 100}}}]}
        if method == "POST" and path == "/pages":
            return {"id": "new-page", "url": "https://notion.so/new-page"}
        if method == "GET":
            return {"results": [{"id": "old-1"}, {"id": "old-2"}], "has_more": False}
        return {}


def test_dry_run_writes_two_daily_pages(run):
    doc, out, cfg = run
    r = pn.publish_client(cfg, out, "TestCo", None, None, dry_run=True)
    pages = [p for p in r["pages"] if p["account"] == te.ACC]
    assert [p["date"] for p in pages] == ["2026-09-30", "2026-10-01"]
    assert all(p["action"] == "dry-run" for p in pages)
    assert any("9002" in w and "no Notion site" in w for w in r["warnings"])
    page = json.load(open(pages[0]["file"]))
    assert page["properties"]["Name"]["title"][0]["text"]["content"] == "30 Sep 2026"
    assert page["properties"]["Status"]["select"]["name"] == "Issues Found"
    text = json.dumps(page["children"])
    assert "Totaliser flow breaks" in text and "TXA03" in text and "Macaddress" in text
    assert "Dispensed (L)" in text and "Items for management" in text
    # every table row has the same width as its header
    for b in page["children"]:
        if b["type"] == "table":
            w = b["table"]["table_width"]
            assert all(len(r["table_row"]["cells"]) == w for r in b["table"]["children"])


def test_creates_when_missing_and_replaces_when_present(run):
    doc, out, cfg = run
    fake = FakeNotion()
    r = pn.publish_client(cfg, out, "TestCo", None, fake)
    mine = [p for p in r["pages"] if p["account"] == te.ACC]
    assert [p["action"] for p in mine] == ["created", "created"]
    creates = [c for c in fake.calls if c[0] == "POST" and c[1] == "/pages"]
    assert creates[0][2]["parent"] == {"type": "data_source_id", "data_source_id": DS}
    assert not [c for c in fake.calls if c[0] == "DELETE"]

    fake2 = FakeNotion(existing={"2026-09-30": [{"id": "p1", "url": "u1"}, {"id": "p2", "url": "u2"}]})
    r2 = pn.publish_client(cfg, out, "TestCo", None, fake2)
    mine = {p["date"]: p["action"] for p in r2["pages"] if p["account"] == te.ACC}
    assert mine == {"2026-09-30": "updated", "2026-10-01": "created"}
    deletes = [c[1] for c in fake2.calls if c[0] == "DELETE"]
    assert deletes == ["/blocks/old-1", "/blocks/old-2"], "only the page's own child blocks are removed"
    assert not any("/pages/p2" in c[1] for c in fake2.calls), "duplicate page left untouched"
    assert any("2 pages share this date" in w for w in r2["warnings"])


def test_refuses_unconfigured_data_source():
    c = pn.NotionClient("tok", "2025-09-03", [DS])
    with pytest.raises(PermissionError):
        c.create("not-allowed", {}, [])


def test_chunking_respects_limits():
    big = [pn.para("x")] * 250 + pn.table(["a"], [["1"]] * 40, 40)
    parts = pn.chunk(big)
    assert all(len(p) <= 90 for p in parts)
    assert sum(len(p) for p in parts) == len(big)


def test_no_pdf_secret_means_no_link(run, monkeypatch):
    doc, out, cfg = run
    monkeypatch.delenv("FAMS_BLOB_CONNECTION_STRING", raising=False)
    pdf = os.path.join(out, "fake.pdf")
    open(pdf, "wb").write(b"%PDF-1.4")
    w = []
    assert pn.upload_pdf(cfg, "TestCo", "2026-10-02", pdf, w) is None
    assert "not set" in w[0]
