"""Run the real test suite and write data/validation.json for the System Validation screen.

    python scripts/validate.py

Nothing here is typed by hand: counts come from pytest's JUnit XML. The screen shows the file's
timestamp so a stale run is visible. Delete the file to make the screen say "not run yet".
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = {
    "test_engine": ("Rule engine", "22 rules × trap cases: partial reversals, retries, caps by date, free-ATM counts"),
    "test_multi_statements": ("Statement merging & history", "duplicates, gaps, verdicts that change when a month appears"),
    "test_ocr": ("Passbook OCR", "multi-line narrations, direction by balance, slip repair"),
    "test_api": ("API & human loop", "scan → answers → guardian → case → approval"),
    "test_notify": ("Real delivery", "mail redirected to the safe address; never to a bank"),
    "test_twin_time_voice": ("Twin, time slider, voice", "twin payloads, as-of recompute, Twilio trial fallback"),
    "test_assistant": ("Assistant", "answers only from findings/rulebook; corrects wrong claims"),
    "test_explain": ("Explainability", "digital twin summary, why-not-flagged, scope, uploads"),
}


def main() -> int:
    xml = Path(tempfile.mkdtemp()) / "junit.xml"
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={xml}"], cwd=ROOT, capture_output=True, text=True)
    if not xml.exists():
        print(proc.stdout[-2000:], proc.stderr[-2000:])
        return 1
    root = ET.parse(xml).getroot()
    suites = root.iter("testsuite") if root.tag == "testsuites" else [root]
    groups: dict[str, dict] = {}
    total = passed = failed = skipped = 0
    for suite in suites:
        for case in suite.iter("testcase"):
            mod = (case.get("classname") or "").split(".")[-1]
            g = groups.setdefault(mod, {"module": mod, "title": GROUPS.get(mod, (mod, ""))[0], "what": GROUPS.get(mod, (mod, ""))[1], "passed": 0, "failed": 0, "skipped": 0, "tests": []})
            status = "passed"
            if case.find("failure") is not None or case.find("error") is not None:
                status = "failed"
            elif case.find("skipped") is not None:
                status = "skipped"
            g[status] += 1
            g["tests"].append({"name": case.get("name"), "status": status})
            total += 1
            passed += status == "passed"
            failed += status == "failed"
            skipped += status == "skipped"
    out = {"ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "python": sys.version.split()[0],
           "total": total, "passed": passed, "failed": failed, "skipped": skipped, "exit_code": proc.returncode,
           "groups": sorted(groups.values(), key=lambda g: -g["passed"])}
    (ROOT / "data" / "validation.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{passed}/{total} passed → data/validation.json")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
