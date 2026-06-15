"""
Update Acceptance Criteria and/or Test Case sections in a Jira ticket.

Usage:
    python tools/jira/update_ticket.py <TICKET-ID> --ac-file ac.md
    python tools/jira/update_ticket.py <TICKET-ID> --tc-table tc.md   # new table format
    python tools/jira/update_ticket.py <TICKET-ID> --ac-file ac.md --append

    --tc-table  reads tc.md in structured TS/TC table format and writes an ADF table
                with numbered rows and checkable TC items to the Test Case field.
    --tc-file   reads tc.md as plain markdown (legacy).

Field keys loaded automatically from fields.json. Override with --ac-field / --tc-field.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

from client import get, put

FIELDS_JSON = Path(__file__).parent / "fields.json"


# ── helpers ──────────────────────────────────────────────────────────────────

def load_project_fields(project_key: str) -> dict:
    if not FIELDS_JSON.exists():
        return {}
    return json.loads(FIELDS_JSON.read_text()).get(project_key, {})


def project_key_from_ticket(ticket_id: str) -> str:
    return ticket_id.split("-")[0].upper()


def _make_id() -> str:
    return str(uuid.uuid4())


def _read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"File not found: {path}")


# ── plain markdown → ADF ─────────────────────────────────────────────────────

def markdown_to_adf(text: str) -> dict:
    lines = text.splitlines()
    content = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            content.append({"type": "codeBlock", "attrs": {},
                             "content": [{"type": "text", "text": "\n".join(code_lines)}]})
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            content.append({"type": "heading", "attrs": {"level": min(level, 6)},
                             "content": [{"type": "text", "text": line.lstrip("#").strip()}]})
            i += 1
            continue
        if line.strip().startswith(("-", "*", "+")):
            items = []
            while i < len(lines) and lines[i].strip().startswith(("-", "*", "+")):
                items.append({"type": "listItem", "content": [{"type": "paragraph",
                    "content": [{"type": "text", "text": lines[i].strip().lstrip("-*+").strip()}]}]})
                i += 1
            content.append({"type": "bulletList", "content": items})
            continue
        if line.strip() and line.strip()[0].isdigit() and ". " in line:
            items = []
            while i < len(lines) and lines[i].strip() and lines[i].strip()[0].isdigit() and ". " in lines[i]:
                items.append({"type": "listItem", "content": [{"type": "paragraph",
                    "content": [{"type": "text", "text": lines[i].strip().split(". ", 1)[-1].strip()}]}]})
                i += 1
            content.append({"type": "orderedList", "content": items})
            continue
        if not line.strip():
            i += 1
            continue
        content.append({"type": "paragraph", "content": [{"type": "text", "text": line.strip()}]})
        i += 1
    return {"version": 1, "type": "doc", "content": content}


# ── append support ────────────────────────────────────────────────────────────

def _fetch_existing_adf(ticket_id: str, field_key: str) -> list:
    data = get(f"/issue/{ticket_id}", params={"fields": field_key})
    val = data.get("fields", {}).get(field_key)
    if isinstance(val, dict) and val.get("type") == "doc":
        return val.get("content", [])
    return []


def merge_adf(existing: list, new_nodes: list) -> dict:
    if not existing:
        return {"version": 1, "type": "doc", "content": new_nodes}
    return {"version": 1, "type": "doc",
            "content": existing + [{"type": "rule"}] + new_nodes}


# ── TC table format parser ────────────────────────────────────────────────────

def parse_tc_table(text: str) -> list:
    """
    Parse structured tc.md into list of scenario dicts.

    Expected block format (one block per TS):

        ### TS-01: Title
        **Type:** Functional
        **Priority:** M

        **Given** precondition text
        **When**
        - step one
        - step two
        **Then**
        - expected result one
        - expected result two

        **TC:**
        [+] Positive test case title
        [-] Negative test case title
    """
    scenarios = []
    current = None
    section = None

    for raw in text.splitlines():
        line = raw.strip()

        if line.startswith("### "):
            if current:
                scenarios.append(current)
            current = {"title": line.lstrip("# ").strip(),
                       "type": "", "priority": "S",
                       "given": [], "when": [], "then": [], "tcs": []}
            section = None
            continue

        if not current:
            continue

        if line.startswith("**Type:**"):
            current["type"] = line[9:].strip()
        elif line.startswith("**Priority:**"):
            current["priority"] = line[13:].strip()
        elif line.startswith("**Given**"):
            section = "given"
            rest = line[9:].strip()
            if rest:
                current["given"].append(rest)
        elif line.startswith("**When**"):
            section = "when"
            rest = line[8:].strip()
            if rest:
                current["when"].append(rest)
        elif line.startswith("**Then**"):
            section = "then"
            rest = line[8:].strip()
            if rest:
                current["then"].append(rest)
        elif line.startswith("**TC:**"):
            section = "tc"
        elif section in ("given", "when", "then") and line.startswith("- "):
            current[section].append(line[2:])
        elif section == "tc" and line[:3] in ("[+]", "[-]"):
            current["tcs"].append(line)

    if current:
        scenarios.append(current)
    return scenarios


# ── ADF table builder ─────────────────────────────────────────────────────────

def _txt(text: str, bold: bool = False) -> dict:
    node = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def _para(*nodes) -> dict:
    return {"type": "paragraph", "content": list(nodes)}


def _cell(content: list) -> dict:
    return {"type": "tableCell", "attrs": {}, "content": content}


def _header_cell(label: str) -> dict:
    return {"type": "tableHeader", "attrs": {},
            "content": [_para(_txt(label, bold=True))]}


def _bullet_list(items: list) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem",
             "content": [_para(_txt(item))]}
            for item in items
        ],
    }


def _scenario_cell(s: dict) -> dict:
    nodes = [_para(_txt(s["title"]))]

    if s["given"]:
        nodes.append(_para(_txt("Given: ")))
        nodes.append(_bullet_list(s["given"]))

    if s["when"]:
        nodes.append(_para(_txt("When: ")))
        nodes.append(_bullet_list(s["when"]))

    if s["then"]:
        nodes.append(_para(_txt("Then: ")))
        nodes.append(_bullet_list(s["then"]))

    return _cell(nodes)


def _tc_evidence_cell(tcs: list) -> dict:
    if not tcs:
        return _cell([_para(_txt(""))])
    task_items = [
        {"type": "taskItem",
         "attrs": {"localId": _make_id(), "state": "TODO"},
         "content": [_txt(tc)]}
        for tc in tcs
    ]
    return _cell([{"type": "taskList",
                   "attrs": {"localId": _make_id()},
                   "content": task_items}])


def scenarios_to_adf_table(scenarios: list) -> dict:
    header = {
        "type": "tableRow",
        "content": [
            _header_cell("Test Scenario"),
            _header_cell("Type"),
            _header_cell("Test Case & Evidence"),
            _header_cell("Priority"),
            _header_cell("Status"),
        ],
    }
    rows = [header]
    for s in scenarios:
        rows.append({
            "type": "tableRow",
            "content": [
                _scenario_cell(s),
                _cell([_para(_txt(s["type"]))]),
                _tc_evidence_cell(s["tcs"]),
                _cell([_para(_txt(s["priority"]))]),
                _cell([_para(_txt(""))]),
            ],
        })
    return {
        "version": 1, "type": "doc",
        "content": [{
            "type": "table",
            "attrs": {"isNumberColumnEnabled": True, "layout": "default"},
            "content": rows,
        }]
    }


# ── payload builder ───────────────────────────────────────────────────────────

def build_payload(ac_text: str, tc_text: str, tc_table_text: str,
                  ac_field: str, tc_field: str,
                  ticket_id: str = "", append: bool = False) -> dict:
    fields = {}

    if ac_text.strip():
        adf = markdown_to_adf(ac_text)
        if append and ticket_id and ac_field:
            existing = _fetch_existing_adf(ticket_id, ac_field)
            adf = merge_adf(existing, adf["content"])
        fields[ac_field] = adf

    if tc_text.strip():
        adf = markdown_to_adf(tc_text)
        if append and ticket_id and tc_field:
            existing = _fetch_existing_adf(ticket_id, tc_field)
            adf = merge_adf(existing, adf["content"])
        fields[tc_field] = adf

    if tc_table_text.strip():
        scenarios = parse_tc_table(tc_table_text)
        if not scenarios:
            sys.exit("No TS blocks found in tc-table file. Check the format.")
        fields[tc_field] = scenarios_to_adf_table(scenarios)

    return {"fields": fields}


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Update AC and/or Test Cases in a Jira ticket.")
    parser.add_argument("ticket_id", help="Jira ticket ID, e.g. PROJ-123")

    parser.add_argument("--ac", help="Acceptance Criteria (inline text)")
    parser.add_argument("--ac-file", help="Acceptance Criteria markdown file")
    parser.add_argument("--tc", help="Test Cases (inline text, plain markdown)")
    parser.add_argument("--tc-file", help="Test Cases markdown file (plain, legacy)")
    parser.add_argument("--tc-table", help="Test Cases file in TS/TC table format → writes ADF table")

    parser.add_argument("--ac-field", help="Override field key for Acceptance Criteria")
    parser.add_argument("--tc-field", help="Override field key for Test Cases")

    parser.add_argument("--append", action="store_true",
                        help="Append AC below existing content (AC only; TC table always overwrites)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print ADF payload without sending to Jira")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    args = parser.parse_args()

    project = project_key_from_ticket(args.ticket_id)
    pf = load_project_fields(project)
    ac_field = args.ac_field or pf.get("acceptance_criteria")
    tc_field = args.tc_field or pf.get("test_case")

    # Resolve sources
    if args.ac and args.ac_file:
        sys.exit("Use either --ac or --ac-file, not both.")
    if args.tc and args.tc_file:
        sys.exit("Use either --tc or --tc-file, not both.")
    if args.tc_file and args.tc_table:
        sys.exit("Use either --tc-file or --tc-table, not both.")

    ac_text = (Path(args.ac_file).read_text(encoding="utf-8") if args.ac_file
               else args.ac or "")
    tc_text = (_read_file(args.tc_file) if args.tc_file else args.tc or "")
    tc_table_text = _read_file(args.tc_table) if args.tc_table else ""

    if not any([ac_text.strip(), tc_text.strip(), tc_table_text.strip()]):
        sys.exit("Nothing to update. Provide --ac/--ac-file, --tc/--tc-file, or --tc-table.")

    if (ac_text.strip() or tc_text.strip() or tc_table_text.strip()) and not ac_field and ac_text.strip():
        sys.exit(f"No AC field key for '{project}'. Run discover_fields.py or pass --ac-field.")
    if (tc_text.strip() or tc_table_text.strip()) and not tc_field:
        sys.exit(f"No TC field key for '{project}'. Run discover_fields.py or pass --tc-field.")

    payload = build_payload(ac_text, tc_text, tc_table_text,
                            ac_field or "", tc_field or "",
                            ticket_id=args.ticket_id, append=args.append)

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not args.yes:
        mode = "APPEND" if args.append else "OVERWRITE"
        print(f"\nAbout to update {args.ticket_id} [{mode}]")
        if ac_text.strip():
            print(f"  AC  : {len(ac_text)} chars")
        if tc_text.strip():
            print(f"  TC  : {len(tc_text)} chars (plain)")
        if tc_table_text.strip():
            n = len(parse_tc_table(tc_table_text))
            print(f"  TC  : {n} scenarios → ADF table")
        if input("\nProceed? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return

    print(f"Updating {args.ticket_id}...", file=sys.stderr)
    put(f"/issue/{args.ticket_id}", payload)
    print(f"Done. Ticket updated: {args.ticket_id}")


if __name__ == "__main__":
    main()
