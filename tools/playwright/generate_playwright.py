"""
Generate Playwright TypeScript spec files from Functional TCs in Jira.

Structure:
  1 Functional TS  →  1 .spec.ts file
  1 TC in that TS  →  1 test() block in the file

TC titles are used as-is (they are atomic and self-descriptive).
Test body implementation details are added separately.

Usage:
    python tools/playwright/generate_playwright.py PROJ-123
    python tools/playwright/generate_playwright.py PROJ-123 --out-dir tests/e2e/
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_adf_tc import fetch_tc_scenarios, render_summary


def _slugify(text: str) -> str:
    text = re.sub(r'\[[\+\-]\]\s*', '', text.lower())
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text.strip())
    return re.sub(r'-+', '-', text)[:60].rstrip('-')


def _render_spec(ts: dict) -> str:
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"// {ts['ts_id']}: {ts['ts_title']}",
        f"// Type: Functional | Priority: {ts['priority']}",
        "",
    ]
    for tc in ts["tcs"]:
        name = f"{tc['label']} {tc['title']}"
        lines += [
            f"test('{name}', async ({{ page }}) => {{",
            "  // TODO: implement",
            "  expect(true).toBe(true);",
            "});",
            "",
        ]
    return "\n".join(lines)


def generate(ticket_id: str, out_dir: Path) -> list[str]:
    functional_ts = fetch_tc_scenarios(ticket_id, functional_only=True)

    if not functional_ts:
        print("No Functional TS found in Jira — nothing to generate.", file=sys.stderr)
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    for ts in functional_ts:
        slug     = _slugify(ts["ts_title"]) or ts["ts_id"].lower().replace("-", "")
        filename = f"{ts['ts_id'].lower()}-{slug}.spec.ts"
        filepath = out_dir / filename
        filepath.write_text(_render_spec(ts), encoding="utf-8")
        generated.append(str(filepath))

    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Generate Playwright specs from Functional TCs in Jira"
    )
    parser.add_argument("ticket_id", help="Jira ticket ID, e.g. PROJ-123")
    parser.add_argument("--out-dir", help="Default: output/<TICKET-ID>/playwright/")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else Path(f"output/{args.ticket_id}/playwright")
    print(f"Output → {out_dir}/", file=sys.stderr)

    files = generate(args.ticket_id, out_dir)
    if files:
        print(f"\nGenerated {len(files)} spec file(s) (1 per Functional TS):")
        for f in files:
            print(f"  {f}")
    else:
        print("No files generated.")


if __name__ == "__main__":
    main()
