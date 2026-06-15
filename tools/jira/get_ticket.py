"""
Fetch a Jira ticket and extract system requirements.

Usage:
    python tools/jira/get_ticket.py <TICKET-ID>
    python tools/jira/get_ticket.py <TICKET-ID> --raw
    python tools/jira/get_ticket.py <TICKET-ID> --json
    python tools/jira/get_ticket.py <TICKET-ID> --fields summary,description,customfield_10016

Field keys for custom fields (AC, TC, QA Feedback, QA person) are loaded from
fields.json. Run discover_fields.py to populate it for a new project.
"""

import argparse
import json
import sys
from pathlib import Path

from client import get
from adf_utils import extract_text, field_text as _field_text_from_utils

FIELDS_JSON = Path(__file__).parent / "fields.json"

BASE_FIELDS = [
    "summary",
    "description",
    "status",
    "issuetype",
    "priority",
    "reporter",
    "assignee",
    "labels",
    "components",
    "customfield_10016",  # Story Points
    "customfield_10014",  # Epic Link
    "subtasks",
    "issuelinks",
    "comment",
    "attachment",
]


def load_project_fields(project_key: str) -> dict:
    if not FIELDS_JSON.exists():
        return {}
    config = json.loads(FIELDS_JSON.read_text())
    return config.get(project_key, {})


def project_key_from_ticket(ticket_id: str) -> str:
    return ticket_id.split("-")[0].upper()


def _field_text(field_value) -> str:
    return _field_text_from_utils(field_value)



def fetch_ticket(ticket_id: str, project_fields: dict = None, extra_fields: list = None) -> dict:
    custom_keys = list((project_fields or {}).values())
    all_fields = BASE_FIELDS + custom_keys + (extra_fields or [])
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for f in all_fields:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return get(f"/issue/{ticket_id}", params={"fields": ",".join(deduped)})


def extract_requirements(data: dict, project_fields: dict = None) -> dict:
    fields = data.get("fields", {})
    pf = project_fields or {}

    linked = []
    for link in fields.get("issuelinks", []):
        direction = "inward" if "inwardIssue" in link else "outward"
        related = link.get("inwardIssue") or link.get("outwardIssue") or {}
        linked.append({
            "type": link.get("type", {}).get("name", ""),
            "direction": direction,
            "key": related.get("key", ""),
            "summary": related.get("fields", {}).get("summary", ""),
        })

    subtasks = [
        {"key": s.get("key"), "summary": s.get("fields", {}).get("summary", "")}
        for s in fields.get("subtasks", [])
    ]

    comments = []
    for c in fields.get("comment", {}).get("comments", []):
        author = c.get("author", {}).get("displayName", "")
        body = _field_text(c.get("body"))
        if body.strip():
            comments.append({"author": author, "body": body.strip()})

    return {
        "key": data.get("key"),
        "url": f"{data.get('self', '').split('/rest/')[0]}/browse/{data.get('key')}",
        "summary": _field_text(fields.get("summary")),
        "type": _field_text(fields.get("issuetype")),
        "status": _field_text(fields.get("status")),
        "priority": _field_text(fields.get("priority")),
        "reporter": _field_text(fields.get("reporter")),
        "assignee": _field_text(fields.get("assignee")),
        "labels": fields.get("labels", []),
        "components": [c.get("name") for c in fields.get("components", [])],
        "description": _field_text(fields.get("description")),
        "acceptance_criteria": _field_text(fields.get(pf.get("acceptance_criteria", "")) if pf.get("acceptance_criteria") else None),
        "test_case": _field_text(fields.get(pf.get("test_case", "")) if pf.get("test_case") else None),
        "qa_feedback": _field_text(fields.get(pf.get("qa_feedback", "")) if pf.get("qa_feedback") else None),
        "linked_tickets": linked,
        "subtasks": subtasks,
        "comments": comments,
    }


def print_requirements(req: dict, project_fields: dict = None) -> None:
    sep = "─" * 60
    has_field_config = bool(project_fields)

    print(f"\n{sep}")
    print(f"  {req['key']}  —  {req['summary']}")
    print(sep)
    print(f"  Type     : {req['type']}")
    print(f"  Status   : {req['status']}")
    print(f"  Priority : {req['priority']}")
    print(f"  Reporter : {req['reporter']}")
    print(f"  Assignee : {req['assignee']}")
    if req["labels"]:
        print(f"  Labels   : {', '.join(req['labels'])}")
    if req["components"]:
        print(f"  Components: {', '.join(req['components'])}")
    print(f"  URL      : {req['url']}")
    print()

    print("## Description / System Requirements")
    print(req["description"] or "(empty)")
    print()

    if has_field_config:
        print("## Acceptance Criteria (QA field)")
        print(req["acceptance_criteria"] or "(empty)")
        print()

        if req.get("test_case"):
            print("## Test Case")
            print(req["test_case"])
            print()

        if req.get("qa_feedback"):
            print("## QA Feedback")
            print(req["qa_feedback"])
            print()
    else:
        print("⚠  No field config found for this project.")
        print(f"   Run: python tools/jira/discover_fields.py {req['key']} --save")
        print()

    if req["subtasks"]:
        print("## Subtasks")
        for s in req["subtasks"]:
            print(f"  - {s['key']}: {s['summary']}")
        print()

    if req["linked_tickets"]:
        print("## Linked Tickets")
        for link in req["linked_tickets"]:
            print(f"  - [{link['type']} / {link['direction']}] {link['key']}: {link['summary']}")
        print()

    if req["comments"]:
        print("## Comments")
        for c in req["comments"]:
            print(f"\n  [{c['author']}]")
            for line in c["body"].splitlines():
                print(f"    {line}")
        print()

    print(sep)


def main():
    parser = argparse.ArgumentParser(description="Fetch a Jira ticket for QA analysis.")
    parser.add_argument("ticket_id", help="Jira ticket ID, e.g. PROJ-123")
    parser.add_argument("--raw", action="store_true", help="Print full raw JSON response")
    parser.add_argument("--json", action="store_true", help="Print extracted requirements as JSON")
    parser.add_argument("--fields", help="Comma-separated extra field keys to fetch")
    args = parser.parse_args()

    project = project_key_from_ticket(args.ticket_id)
    project_fields = load_project_fields(project)

    if not project_fields:
        print(f"⚠  No field config for project '{project}' in fields.json.", file=sys.stderr)
        print(f"   Run: python tools/jira/discover_fields.py {args.ticket_id} --save", file=sys.stderr)

    extra = args.fields.split(",") if args.fields else []

    print(f"Fetching {args.ticket_id} from Jira...", file=sys.stderr)
    data = fetch_ticket(args.ticket_id, project_fields=project_fields, extra_fields=extra)

    if args.raw:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    req = extract_requirements(data, project_fields=project_fields)

    if args.json:
        print(json.dumps(req, indent=2, ensure_ascii=False))
        return

    print_requirements(req, project_fields=project_fields)


if __name__ == "__main__":
    main()
