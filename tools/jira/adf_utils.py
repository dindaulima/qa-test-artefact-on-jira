"""
Shared Atlassian Document Format (ADF) utilities.

Single source of truth for ADF text extraction and TC table parsing.
Imported by any tool that reads Jira field content:
  - tools/jira/get_ticket.py        (text extraction for all fields)
  - tools/playwright/parse_adf_tc.py (TC table → structured TS/TC data)
  - tools/report/parse_results.py   (TC table → test result parsing)
"""

import re

_TS_PREFIX = re.compile(r'^(TS-\d+)\s*[:\-–]\s*(.+)$')
_TC_LABEL  = re.compile(r'^(\[\+\]|\[-\])\s+(.+)$')


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(node) -> str:
    """
    Recursively extract plain text from any ADF node or list of nodes.

    Handles all standard node types including table, taskList, and taskItem.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        ntype   = node.get("type", "")
        text    = node.get("text", "")
        content = node.get("content", [])

        if ntype == "hardBreak":
            return "\n"
        if ntype in ("bulletList", "orderedList"):
            items = []
            for i, child in enumerate(content):
                prefix = f"{i + 1}." if ntype == "orderedList" else "-"
                items.append(f"{prefix} {extract_text(child).strip()}")
            return "\n".join(items)
        if ntype == "listItem":
            return extract_text({"type": "doc", "content": content})
        if ntype == "heading":
            level  = node.get("attrs", {}).get("level", 2)
            return f"\n{'#' * level} {''.join(extract_text(c) for c in content)}\n"
        if ntype == "paragraph":
            return "".join(extract_text(c) for c in content) + "\n"
        if ntype == "codeBlock":
            return f"```\n{''.join(extract_text(c) for c in content)}\n```\n"
        if ntype in ("table", "tableRow"):
            return "".join(extract_text(c) for c in content)
        if ntype in ("tableCell", "tableHeader"):
            return "".join(extract_text(c) for c in content) + "\t"
        if ntype == "taskList":
            return "".join(extract_text(c) for c in content)
        if ntype == "taskItem":
            return "".join(extract_text(c) for c in content) + "\n"
        if text:
            return text
        return "".join(extract_text(c) for c in content)

    if isinstance(node, list):
        return "".join(extract_text(n) for n in node)
    return ""


def field_text(field_value) -> str:
    """
    Extract a display string from any Jira field value (ADF doc, string, or object).
    Drop-in replacement for the private _field_text in get_ticket.py.
    """
    if field_value is None:
        return ""
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, dict):
        if field_value.get("type") == "doc":
            return extract_text(field_value).strip()
        return (
            field_value.get("displayName")
            or field_value.get("name")
            or field_value.get("value")
            or ""
        )
    return str(field_value)


# ── TC table parsing ──────────────────────────────────────────────────────────

def _cell_text(cell: dict) -> str:
    return extract_text(cell.get("content", [])).strip()


def _parse_scenario_cell(cell: dict) -> dict:
    """
    Parse the Test Scenario cell into ts_id, ts_title, and Given/When/Then lists.

    ADF structure written by update_ticket.py --tc-table:
      paragraph  → "TS-XX: title"
      paragraph  → "Given"  (or "Given:")
      bulletList → precondition items
      paragraph  → "When"   (or "When:")
      bulletList → step items
      paragraph  → "Then"   (or "Then:")
      bulletList → outcome items
    """
    ts_id, ts_title = "", ""
    given, when, then_ = [], [], []
    section = None

    for node in cell.get("content", []):
        ntype = node.get("type", "")

        if ntype == "paragraph":
            text = extract_text(node.get("content", [])).strip()
            key  = text.lower().rstrip(": ")

            if key == "given":
                section = "given"
            elif key == "when":
                section = "when"
            elif key == "then":
                section = "then"
            elif section is None and text:
                m = _TS_PREFIX.match(text)
                if m:
                    ts_id    = m.group(1)
                    ts_title = m.group(2).strip()
                else:
                    ts_title = text

        elif ntype == "bulletList" and section is not None:
            for item in node.get("content", []):
                item_text = extract_text(item.get("content", [])).strip()
                if not item_text:
                    continue
                if section == "given":
                    given.append(item_text)
                elif section == "when":
                    when.append(item_text)
                elif section == "then":
                    then_.append(item_text)

    return {"ts_id": ts_id, "ts_title": ts_title, "given": given, "when": when, "then": then_}


def _parse_tc_cell(cell: dict) -> list[dict]:
    """Extract TC list from the Test Case & Evidence cell (taskList of taskItems)."""
    tcs = []
    for node in cell.get("content", []):
        if node.get("type") != "taskList":
            continue
        for task in node.get("content", []):
            if task.get("type") != "taskItem":
                continue
            text = extract_text(task.get("content", [])).strip()
            m = _TC_LABEL.match(text)
            if m:
                tcs.append({"label": m.group(1), "title": m.group(2).strip()})
            elif text:
                tcs.append({"label": "", "title": text})
    return tcs


def _detect_columns(header_row: dict) -> dict:
    """
    Map column roles to their indices by reading the header text.
    Handles both the current format ("Type" column) and older formats ("AC" column).
    """
    col = {"scenario": 0, "type": -1, "tc": -1, "priority": -1}
    for i, cell in enumerate(header_row.get("content", [])):
        label = _cell_text(cell).lower()
        if "scenario" in label:
            col["scenario"] = i
        elif label in ("type", "tipe"):
            col["type"] = i
        elif "case" in label or "evidence" in label:
            col["tc"] = i
        elif "priority" in label or "prioritas" in label:
            col["priority"] = i
    return col


def parse_tc_table(adf: dict) -> list[dict]:
    """
    Parse an ADF document (TC field value from Jira) into a list of TS/TC dicts.

    Returns all scenarios regardless of type. Use filter_by_type() to narrow down.

    Each item shape:
    {
        "ts_id":    "TS-01",
        "ts_title": "Admin dapat membuat voucher baru",
        "type":     "Functional",
        "priority": "M",
        "given":    ["precondition 1", ...],
        "when":     ["step 1", ...],
        "then":     ["outcome 1", ...],
        "tcs": [
            {"label": "[+]", "title": "Admin dapat membuat voucher baru dengan data valid"},
            {"label": "[-]", "title": "Admin tidak bisa mengosongkan nama voucher"},
        ],
    }
    """
    if not isinstance(adf, dict) or adf.get("type") != "doc":
        return []

    table = next(
        (n for n in adf.get("content", []) if n.get("type") == "table"),
        None,
    )
    if table is None:
        return []

    rows = table.get("content", [])
    if len(rows) < 2:
        return []

    col = _detect_columns(rows[0])

    def get_cell(row_cells: list, key: str) -> dict:
        idx = col.get(key, -1)
        return row_cells[idx] if 0 <= idx < len(row_cells) else {}

    scenarios = []
    for ts_index, row in enumerate(rows[1:], start=1):
        cells = row.get("content", [])
        if not cells:
            continue

        scenario = _parse_scenario_cell(get_cell(cells, "scenario"))
        if not scenario["ts_id"]:
            scenario["ts_id"] = f"TS-{ts_index:02d}"

        scenarios.append({
            "ts_id":    scenario["ts_id"],
            "ts_title": scenario["ts_title"],
            "type":     _cell_text(get_cell(cells, "type")),
            "priority": _cell_text(get_cell(cells, "priority")),
            "given":    scenario["given"],
            "when":     scenario["when"],
            "then":     scenario["then"],
            "tcs":      _parse_tc_cell(get_cell(cells, "tc")),
        })

    return scenarios


def filter_by_type(scenarios: list[dict], ts_type: str = "functional") -> list[dict]:
    """Filter TS list by type string (case-insensitive)."""
    return [s for s in scenarios if s["type"].strip().lower() == ts_type.lower()]
