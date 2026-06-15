"""
List all available Jira fields for a project — use this to find custom field keys
for Acceptance Criteria and Test Case sections in your Jira instance.

Usage:
    python tools/jira/list_fields.py
    python tools/jira/list_fields.py --search "acceptance"
    python tools/jira/list_fields.py --search "test"
"""

import argparse

from client import get


def main():
    parser = argparse.ArgumentParser(description="List Jira fields to find custom field keys.")
    parser.add_argument("--search", help="Filter fields by name (case-insensitive)")
    args = parser.parse_args()

    fields = get("/field")
    results = sorted(fields, key=lambda f: f.get("name", "").lower())

    if args.search:
        query = args.search.lower()
        results = [f for f in results if query in f.get("name", "").lower() or query in f.get("id", "").lower()]

    print(f"\n{'Key':<30} {'Name':<40} {'Type'}")
    print("─" * 90)
    for field in results:
        key = field.get("id", "")
        name = field.get("name", "")
        schema = field.get("schema", {})
        field_type = schema.get("custom") or schema.get("type") or ""
        print(f"{key:<30} {name:<40} {field_type}")


if __name__ == "__main__":
    main()
