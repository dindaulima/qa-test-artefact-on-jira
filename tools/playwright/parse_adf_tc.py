"""
Fetch and parse the TC ADF table from Jira.

ADF parsing is handled entirely by tools/jira/adf_utils.py.
This module only handles the Jira fetch and result presentation.

Usage:
    python tools/playwright/parse_adf_tc.py PROJ-123
    python tools/playwright/parse_adf_tc.py PROJ-123 --json
    python tools/playwright/parse_adf_tc.py PROJ-123 --all-types
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "jira"))
from get_ticket import fetch_ticket, load_project_fields, project_key_from_ticket
from adf_utils import filter_by_type, parse_tc_table


def fetch_tc_scenarios(ticket_id: str, functional_only: bool = True) -> list[dict]:
    """Fetch TC field from Jira, parse the ADF table, and return TS/TC list."""
    project = project_key_from_ticket(ticket_id)
    pf      = load_project_fields(project)

    if not pf.get("test_case"):
        sys.exit(
            f"No test_case field configured for project '{project}'.\n"
            f"Run: python tools/jira/discover_fields.py {ticket_id} --save"
        )

    print(f"Fetching {ticket_id}…", file=sys.stderr)
    data = fetch_ticket(ticket_id, project_fields=pf)
    raw  = data.get("fields", {}).get(pf["test_case"])

    if not raw:
        print("Test Case field is empty in Jira.", file=sys.stderr)
        return []

    scenarios = parse_tc_table(raw)
    return filter_by_type(scenarios) if functional_only else scenarios


def render_summary(scenarios: list[dict]) -> str:
    if not scenarios:
        return "No Functional TS found in Jira Test Case field."
    total = sum(len(s["tcs"]) for s in scenarios)
    lines = [f"Functional TS: {len(scenarios)}  |  Total TCs: {total}\n"]
    for s in scenarios:
        lines.append(f"  {s['ts_id']}: {s['ts_title']}  [Priority: {s['priority']}]")
        for i, tc in enumerate(s["tcs"], 1):
            lines.append(f"    {i:2d}. {tc['label']} {tc['title']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Parse TC ADF table from Jira — Functional TS/TCs only"
    )
    parser.add_argument("ticket_id", help="Jira ticket ID, e.g. PROJ-123")
    parser.add_argument("--json",      action="store_true", help="Output as JSON")
    parser.add_argument("--all-types", action="store_true",
                        help="Include all TS types (default: Functional only)")
    args = parser.parse_args()

    scenarios = fetch_tc_scenarios(args.ticket_id, functional_only=not args.all_types)

    if args.json:
        print(json.dumps(scenarios, indent=2, ensure_ascii=False))
    else:
        print(render_summary(scenarios))


if __name__ == "__main__":
    main()
