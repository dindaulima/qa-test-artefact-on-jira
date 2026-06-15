# Jira Tools — Skill Reference for QAanalyst

These Python scripts power the Jira integration for the QAanalyst agent.
Run all scripts from the project root (`myQA/`).

---

## Setup

### 1. Buat dan aktifkan virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

Untuk sesi berikutnya, cukup aktifkan ulang:

```bash
source .venv/bin/activate
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

To generate a Jira API token: Jira → Account Settings → Security → API tokens.

### 3. Find your custom field keys (one-time setup)

```bash
cd tools/jira
python list_fields.py --search "acceptance"
python list_fields.py --search "test"
```

Note the field key (e.g. `customfield_10500`) for Acceptance Criteria and Test Cases.
Update `--ac-field` and `--tc-field` defaults in `update_ticket.py` to match.

---

## Tools

### `get_ticket.py` — Fetch ticket and extract requirements

```bash
# Default: human-readable summary
python tools/jira/get_ticket.py PROJ-123

# JSON output (for piping or parsing)
python tools/jira/get_ticket.py PROJ-123 --json

# Raw Jira API response
python tools/jira/get_ticket.py PROJ-123 --raw

# Include extra fields
python tools/jira/get_ticket.py PROJ-123 --fields customfield_10200,customfield_10300
```

**Output includes:**
- Ticket key, URL, type, status, priority, reporter, assignee
- Description / system requirements (ADF converted to readable text)
- Existing Acceptance Criteria (if any)
- Subtasks and linked tickets
- Comments

---

### `update_ticket.py` — Write AC and/or TC back to Jira

```bash
# Write AC from a file
python tools/jira/update_ticket.py PROJ-123 --ac-file ac.md

# Write TC from a file
python tools/jira/update_ticket.py PROJ-123 --tc-file tc.md

# Write both at once
python tools/jira/update_ticket.py PROJ-123 --ac-file ac.md --tc-file tc.md

# Inline text
python tools/jira/update_ticket.py PROJ-123 --ac "AC-F1: User can log in"

# Preview payload without sending (dry run)
python tools/jira/update_ticket.py PROJ-123 --ac-file ac.md --dry-run

# Skip confirmation prompt
python tools/jira/update_ticket.py PROJ-123 --ac-file ac.md --yes

# Use custom field keys
python tools/jira/update_ticket.py PROJ-123 \
  --ac-file ac.md \
  --ac-field customfield_10500 \
  --tc-file tc.md \
  --tc-field customfield_10501
```

**Behavior:**
- Shows a preview and asks for confirmation before updating (unless `--yes`).
- Converts Markdown input to Atlassian Document Format (ADF) automatically.
- Supports headings, bullet lists, numbered lists, code blocks, and paragraphs.

---

### `list_fields.py` — Discover Jira field keys

```bash
# List all fields
python tools/jira/list_fields.py

# Search by name
python tools/jira/list_fields.py --search "acceptance"
python tools/jira/list_fields.py --search "test case"
```

---

## How QAanalyst Uses These Tools

| Agent Step | Tool |
|---|---|
| Fetch ticket & requirements | `get_ticket.py TICKET-ID` |
| Check existing AC | included in `get_ticket.py` output |
| Write AC to Jira | `update_ticket.py TICKET-ID --ac-file ac.md` |
| Write TS & TC to Jira | `update_ticket.py TICKET-ID --tc-file tc.md` |
| Discover field keys | `list_fields.py --search "..."` |

---

## Workflow with QAanalyst

```bash
# Step 1: Fetch and review the ticket
python tools/jira/get_ticket.py PROJ-123

# Step 2: QAanalyst generates AC → save output to file
# (copy AC from QAanalyst response into ac.md)

# Step 3: QAanalyst generates TS+TC → save output to file
# (copy TS+TC from QAanalyst response into tc.md)

# Step 4: Preview what will be written
python tools/jira/update_ticket.py PROJ-123 --ac-file ac.md --tc-file tc.md --dry-run

# Step 5: Write to Jira (with confirmation prompt)
python tools/jira/update_ticket.py PROJ-123 --ac-file ac.md --tc-file tc.md
```
