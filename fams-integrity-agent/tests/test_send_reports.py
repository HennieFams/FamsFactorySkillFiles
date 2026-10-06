import json, os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import send_reports as sr

CFG = {"email": {"endpoint": "https://example.invalid/send", "recipients": ["a@x", "b@x"],
                 "subject": "FAMS Integrity Report — {client} — {date}", "timeout_seconds": 5}}


def make_run(tmp, clients=("ShipTech", "PMC-Phalaborwa"), layout="reports"):
    tmp.mkdir(parents=True, exist_ok=True)
    cfgp = tmp / "config.json"; cfgp.write_text(json.dumps(CFG))
    run = tmp / "run"
    for c in clients:
        (run / c).mkdir(parents=True)
        (run / c / "findings.json").write_text(json.dumps({
            "client": c, "client_short": c, "window": {"report_date": "2026-10-06",
            "start_sast": "2026-10-04 06:00 SAST", "end_sast": "2026-10-06 06:00 SAST"},
            "kpis": {"investigate": 3, "monitor": 5}, "accounts": [{"AccountID": 1}], "data_gaps": []}))
        d = run / "reports" if layout == "reports" else run / c
        d.mkdir(exist_ok=True)
        (d / f"FAMS-Integrity-{c}-2026-10-06.pdf").write_bytes(b"%PDF-1.4 test")
    return cfgp, run


def args(cfgp, run, **kw):
    a = dict(run_dir=str(run), client=None, pdf=[], to=None, resend=False, dry_run=False, config=str(cfgp))
    a.update(kw); return types.SimpleNamespace(**a)


def test_sends_each_pdf_to_each_recipient_once(tmp_path, capsys):
    cfgp, run = make_run(tmp_path)
    calls = []
    poster = lambda ep, p, t: (calls.append(p) or (200, "ok"))
    assert sr.run(args(cfgp, run), poster) == 0
    assert len(calls) == 4
    assert {(c["email"], c["fileName"]) for c in calls} == {
        (r, f"FAMS-Integrity-{c}-2026-10-06.pdf") for r in ("a@x", "b@x") for c in ("ShipTech", "PMC-Phalaborwa")}
    assert calls[0]["subject"].startswith("FAMS Integrity Report — ")
    assert "3 Investigate, 5 Monitor" in calls[0]["body"]
    # re-run sends nothing
    calls.clear()
    assert sr.run(args(cfgp, run), poster) == 0
    assert calls == []


def test_failure_retried_once_then_reported_and_only_failed_resent(tmp_path, monkeypatch):
    monkeypatch.setattr(sr.time, "sleep", lambda s: None)
    cfgp, run = make_run(tmp_path, clients=("ShipTech",), layout="client")
    calls = []
    def poster(ep, p, t):
        calls.append(p["email"])
        return (500, "boom") if p["email"] == "b@x" else (200, "ok")
    assert sr.run(args(cfgp, run), poster) == 2
    assert calls.count("b@x") == 2 and calls.count("a@x") == 1
    calls.clear()
    assert sr.run(args(cfgp, run), lambda ep, p, t: (calls.append(p["email"]) or (200, "ok"))) == 0
    assert calls == ["b@x"]


def test_missing_pdf_and_dry_run(tmp_path):
    cfgp, run = make_run(tmp_path, clients=("ShipTech",))
    os.remove(run / "reports" / "FAMS-Integrity-ShipTech-2026-10-06.pdf")
    assert sr.run(args(cfgp, run), lambda *a: (200, "")) == 2
    cfgp, run = make_run(tmp_path / "b", clients=("ShipTech",))
    called = []
    assert sr.run(args(cfgp, run, dry_run=True), lambda *a: called.append(1)) == 0
    assert called == [] and not os.path.exists(run / "email_log.json")
