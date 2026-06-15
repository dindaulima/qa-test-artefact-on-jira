"""
Discover custom field keys for a Jira project by inspecting a ticket's editmeta.
Helps identify the correct field keys for Acceptance Criteria, Test Case,
and QA Feedback — which differ per project in multi-project Jira instances.

Usage:
    python tools/jira/discover_fields.py PROJ-123
    python tools/jira/discover_fields.py PROJ-123 --all
    python tools/jira/discover_fields.py PROJ-123 --save
    python tools/jira/discover_fields.py PROJ-123 --search "acceptance"

Options:
    --all       Show all editable fields, not just QA/AC-related ones
    --search    Filter fields by keyword (case-insensitive)
    --save      Interactively map and save field keys to fields.json
"""

import argparse
import json
import sys
from pathlib import Path

from client import get

FIELDS_JSON = Path(__file__).parent / "fields.json"

QA_KEYWORDS = ["accept", "test case", "feedback"]

KNOWN_ROLES = {
    "acceptance_criteria": ["acceptance criteria", "acceptances criteria"],
    "test_case":           ["test case"],
    "qa_feedback":         ["qa feedback"],
}


def load_fields_json() -> dict:
    if FIELDS_JSON.exists():
        return json.loads(FIELDS_JSON.read_text())
    return {}


def save_fields_json(data: dict) -> None:
    FIELDS_JSON.write_text(json.dumps(data, indent=2) + "\n")


def project_key_from_ticket(ticket_id: str) -> str:
    return ticket_id.split("-")[0].upper()


def fetch_editmeta(ticket_id: str) -> dict:
    data = get(f"/issue/{ticket_id}/editmeta")
    return data.get("fields", {})


def auto_detect(editmeta: dict) -> dict:
    """Try to automatically map field roles to keys based on known name patterns."""
    detected = {}
    for key, meta in editmeta.items():
        name = meta.get("name", "").lower()
        for role, patterns in KNOWN_ROLES.items():
            if role in detected:
                continue
            if any(p == name for p in patterns):
                detected[role] = key
    return detected


def print_fields(editmeta: dict, keywords: list = None, show_all: bool = False) -> None:
    print(f"\n{'Key':<30} {'Name':<35} {'Type'}")
    print("─" * 90)
    for key, meta in sorted(editmeta.items()):
        name = meta.get("name", "")
        schema = meta.get("schema", {})
        ftype = schema.get("custom", "") or schema.get("type", "")
        if show_all or (keywords and any(kw in name.lower() for kw in keywords)):
            print(f"{key:<30} {name:<35} {ftype}")


def interactive_save(editmeta: dict, project: str) -> None:
    existing = load_fields_json()
    current = existing.get(project, {})

    auto = auto_detect(editmeta)
    if auto:
        print(f"\nAuto-detected fields for {project}:")
        for role, key in auto.items():
            name = editmeta.get(key, {}).get("name", "")
            print(f"  {role:<25} → {key}  ({name})")

    print(f"\nConfigure field mapping for project '{project}'.")
    print("Press Enter to accept auto-detected value, or type a custom field key.\n")

    mapping = {}
    for role in KNOWN_ROLES:
        auto_key = auto.get(role, current.get(role, ""))
        auto_name = editmeta.get(auto_key, {}).get("name", "") if auto_key else ""
        hint = f" [{auto_key} — {auto_name}]" if auto_key else " [not detected]"
        answer = input(f"  {role}{hint}: ").strip()
        mapping[role] = answer if answer else auto_key

    mapping = {k: v for k, v in mapping.items() if v}
    existing[project] = mapping
    save_fields_json(existing)
    print(f"\nSaved to {FIELDS_JSON}:")
    print(json.dumps({project: mapping}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Discover Jira custom field keys for a project.")
    parser.add_argument("ticket_id", help="Any ticket from the target project, e.g. PROJ-123")
    parser.add_argument("--all", action="store_true", help="Show all editable fields")
    parser.add_argument("--search", help="Filter by keyword")
    parser.add_argument("--save", action="store_true",
                        help="Interactively map and save field keys to fields.json")
    args = parser.parse_args()

    project = project_key_from_ticket(args.ticket_id)
    print(f"Fetching field metadata for project: {project} (via {args.ticket_id})", file=sys.stderr)

    editmeta = fetch_editmeta(args.ticket_id)

    keywords = [args.search.lower()] if args.search else QA_KEYWORDS
    print_fields(editmeta, keywords=keywords, show_all=args.all)

    if not args.save:
        auto = auto_detect(editmeta)
        if auto:
            print(f"\nAuto-detected mapping for '{project}':")
            for role, key in auto.items():
                name = editmeta.get(key, {}).get("name", "")
                print(f"  {role:<25} → {key}  ({name})")
            print(f"\nRun with --save to save this mapping to {FIELDS_JSON}")
        return

    interactive_save(editmeta, project)


if __name__ == "__main__":
    main()
