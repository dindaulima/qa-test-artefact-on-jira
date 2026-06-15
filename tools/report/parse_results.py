"""
Parse QA test results from a Jira ticket's test_case field.

Usage:
    python tools/report/parse_results.py <TICKET-ID>
    python tools/report/parse_results.py <TICKET-ID> --json
    python tools/report/parse_results.py <TICKET-ID> --save output/TICKET-ID/report.md

Status detection in TC blocks (case-insensitive):
    **Result:** PASS / LULUS / ✅   → pass
    **Result:** FAIL / GAGAL / ❌   → fail
    **Result:** BLOCKED / BLOKIR / 🚫 → blocked
    **Result:** SKIP / LEWATI / ⏭  → skip
    (no Result field)               → pending

Emoji may also appear directly in the TC header line.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# Allow importing from tools/jira
sys.path.insert(0, str(Path(__file__).parent.parent / "jira"))
from get_ticket import extract_requirements, fetch_ticket, load_project_fields, project_key_from_ticket

# ── Status constants ──────────────────────────────────────────────────────────
PASS = "pass"
FAIL = "fail"
BLOCKED = "blocked"
SKIP = "skip"
PENDING = "pending"

_PASS_RE    = re.compile(r"\b(PASS|LULUS|PASSED)\b|✅", re.IGNORECASE)
_FAIL_RE    = re.compile(r"\b(FAIL|GAGAL|FAILED)\b|❌", re.IGNORECASE)
_BLOCKED_RE = re.compile(r"\b(BLOCKED|BLOKIR)\b|🚫", re.IGNORECASE)
_SKIP_RE    = re.compile(r"\b(SKIP|SKIPPED|LEWATI)\b|⏭", re.IGNORECASE)

_RESULT_LINE = re.compile(r"^\*\*(Result|Status)\*\*\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_NOTES_LINE  = re.compile(r"^\*\*Notes?\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE)
_TC_HEADER   = re.compile(r"^#{1,4}\s+(TC-\d+)\s*[:\-–]\s*(.+)$", re.MULTILINE)
_TS_HEADER   = re.compile(r"^#{1,4}\s+(TS-\d+)\s*[:\-–]\s*(.+)$", re.MULTILINE)
_SCENARIO    = re.compile(r"\*\*Scenario\*\*\s*:\s*(TS-\d+)", re.IGNORECASE)

EMOJI = {PASS: "✅", FAIL: "❌", BLOCKED: "🚫", SKIP: "⏭", PENDING: "⏳"}
LABEL = {PASS: "PASS", FAIL: "FAIL", BLOCKED: "BLOCKED", SKIP: "SKIP", PENDING: "PENDING"}


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _classify(text: str) -> str:
    if _PASS_RE.search(text):    return PASS
    if _FAIL_RE.search(text):    return FAIL
    if _BLOCKED_RE.search(text): return BLOCKED
    if _SKIP_RE.search(text):    return SKIP
    return PENDING


def parse_ts_list(content: str) -> list[dict]:
    return [
        {"id": m.group(1), "name": m.group(2).strip()}
        for m in _TS_HEADER.finditer(content or "")
    ]


def parse_tc_blocks(content: str) -> list[dict]:
    if not content:
        return []
    headers = list(_TC_HEADER.finditer(content))
    if not headers:
        return []

    blocks = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        block = content[start:end]

        # Status: prefer explicit **Result:** field, fall back to emoji in header
        result_match = _RESULT_LINE.search(block)
        if result_match:
            status = _classify(result_match.group(2))
        else:
            status = _classify(m.group(0))  # check header line for emoji

        # Notes after the Result line
        notes = ""
        if result_match:
            after = block[result_match.end():]
            nm = _NOTES_LINE.search(after)
            if nm:
                notes = nm.group(1).strip()

        sc_match = _SCENARIO.search(block)

        blocks.append({
            "id": m.group(1),
            "name": m.group(2).strip(),
            "scenario": sc_match.group(1) if sc_match else "",
            "status": status,
            "notes": notes,
        })
    return blocks


def compute_metrics(tc_blocks: list[dict]) -> dict:
    counts = {PASS: 0, FAIL: 0, BLOCKED: 0, SKIP: 0, PENDING: 0}
    for tc in tc_blocks:
        counts[tc["status"]] += 1
    total = len(tc_blocks)
    executed = total - counts[PENDING] - counts[SKIP]
    pass_rate = round(counts[PASS] / executed * 100, 1) if executed > 0 else 0.0
    return {**counts, "total": total, "executed": executed, "pass_rate": pass_rate}


def group_by_scenario(tc_blocks: list[dict]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for tc in tc_blocks:
        groups.setdefault(tc["scenario"] or "—", []).append(tc)
    return groups


# ── Main fetch + parse ────────────────────────────────────────────────────────

def parse_results(ticket_id: str) -> dict:
    project = project_key_from_ticket(ticket_id)
    pf = load_project_fields(project)
    data = fetch_ticket(ticket_id, project_fields=pf)
    req = extract_requirements(data, project_fields=pf)

    tc_content = req.get("test_case") or ""
    ts_list  = parse_ts_list(tc_content)
    tc_blocks = parse_tc_blocks(tc_content)
    metrics  = compute_metrics(tc_blocks)

    return {
        "ticket": {
            "key":      req["key"],
            "url":      req["url"],
            "summary":  req["summary"],
            "status":   req["status"],
            "assignee": req["assignee"] or "—",
        },
        "ts_count":    len(ts_list),
        "ts_list":     ts_list,
        "tc_blocks":   tc_blocks,
        "metrics":     metrics,
        "qa_feedback": req.get("qa_feedback") or "",
        "report_date": str(date.today()),
    }


# ── Report renderer ───────────────────────────────────────────────────────────

def render_report(r: dict) -> str:
    t  = r["ticket"]
    m  = r["metrics"]
    tcs = r["tc_blocks"]
    tss = r["ts_list"]
    qa  = r["qa_feedback"]
    lines = []

    def row(*cols): lines.append("| " + " | ".join(str(c) for c in cols) + " |")

    lines += [
        f"# Test Execution Report — {t['key']}\n",
        f"**Feature:** {t['summary']}",
        f"**Ticket:** {t['url']}",
        f"**Status:** {t['status']}",
        f"**Assignee:** {t['assignee']}",
        f"**Report Date:** {r['report_date']}",
        "", "---", "",
    ]

    # Summary
    lines += ["## Summary\n", "| Metric | Value |", "|---|---|"]
    row("Test Scenarios", r["ts_count"])
    row("Test Cases", m["total"])
    row("✅ Passed",  m[PASS])
    row("❌ Failed",  m[FAIL])
    row("🚫 Blocked", m[BLOCKED])
    row("⏭ Skipped",  m[SKIP])
    row("⏳ Pending",  m[PENDING])
    row("**Pass Rate**", f"**{m['pass_rate']}%**")
    lines += ["", "---", ""]

    # Per-scenario breakdown
    if tcs:
        lines += ["## Status per Test Scenario\n",
                  "| Scenario | TC | ✅ | ❌ | 🚫 | ⏭ | ⏳ |",
                  "|---|---|---|---|---|---|---|"]
        groups = group_by_scenario(tcs)
        for ts in tss:
            bucket = groups.get(ts["id"], [])
            if not bucket:
                continue
            def cnt(s): return sum(1 for tc in bucket if tc["status"] == s)
            name = ts["name"][:55] + ("…" if len(ts["name"]) > 55 else "")
            row(f"**{ts['id']}** {name}", len(bucket),
                cnt(PASS), cnt(FAIL), cnt(BLOCKED), cnt(SKIP), cnt(PENDING))
        unlinked = groups.get("—", [])
        if unlinked:
            def cnt(s): return sum(1 for tc in unlinked if tc["status"] == s)
            row("_(no scenario)_", len(unlinked),
                cnt(PASS), cnt(FAIL), cnt(BLOCKED), cnt(SKIP), cnt(PENDING))
        lines += ["", "---", ""]

    # Full TC table
    if tcs:
        lines += ["## Test Case Results\n",
                  "| ID | Test Case | Scenario | Status |",
                  "|---|---|---|---|"]
        for tc in tcs:
            name = tc["name"][:55] + ("…" if len(tc["name"]) > 55 else "")
            row(tc["id"], name, tc["scenario"], f"{EMOJI[tc['status']]} {LABEL[tc['status']]}")
        lines += ["", "---", ""]

    # Issues detail
    issues = [tc for tc in tcs if tc["status"] in (FAIL, BLOCKED)]
    if issues:
        lines += ["## Issues Found\n"]
        for tc in issues:
            lines += [
                f"### {EMOJI[tc['status']]} {tc['id']}: {tc['name']}\n",
                f"**Scenario:** {tc['scenario']}",
                f"**Status:** {LABEL[tc['status']]}",
            ]
            if tc["notes"]:
                lines.append(f"**Notes:** {tc['notes']}")
            lines.append("")
        lines += ["---", ""]

    if qa:
        lines += ["## QA Notes\n", qa, ""]

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Parse QA test results from a Jira ticket.")
    parser.add_argument("ticket_id", help="Jira ticket ID, e.g. PROJ-123")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of Markdown report")
    parser.add_argument("--save", metavar="FILE", help="Save report to file (default: stdout)")
    args = parser.parse_args()

    print(f"Fetching {args.ticket_id}…", file=sys.stderr)
    result = parse_results(args.ticket_id)

    output = json.dumps(result, indent=2, ensure_ascii=False) if args.json else render_report(result)

    if args.save:
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        Path(args.save).write_text(output, encoding="utf-8")
        print(f"Report saved → {args.save}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
