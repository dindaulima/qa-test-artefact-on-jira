# myQA — QA Analyst Agent

Agent berbasis AI untuk menghasilkan Acceptance Criteria (AC), Test Scenarios (TS), dan Test Cases (TC) dari tiket Jira, lalu menuliskannya langsung ke Jira.

---

## Prasyarat

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Kredensial Jira

```bash
cp .env.example .env
```

Isi `.env`:

```
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

> Buat API token: Jira → Account Settings → Security → API tokens.

### 3. Node.js & Playwright (untuk automation test)

```bash
npm install
npx playwright install chromium
```

Ini menginstall `@playwright/test` dan browser Chromium. MCP Playwright berjalan otomatis via `npx` (tidak perlu install global) — konfigurasi sudah ada di `.mcp.json`.

**Menjalankan automation test:**

```bash
npm test                  # headless (default)
npm run test:headed       # dengan browser tampil
npm run test:debug        # mode debug interaktif
npm run test:report       # tampilkan laporan HTML
```

Atau run satu file saja:

```bash
npx playwright test output/BRAVO-1169/playwright/ts-01-*.spec.ts
```

---

### 4. Setup field key per project (sekali saja)

Setiap Jira project punya custom field key yang berbeda untuk AC dan Test Case. Jalankan sekali per project:

```bash
source .venv/bin/activate
python tools/jira/discover_fields.py PROJ-123 --save
```

Field key tersimpan otomatis di `tools/jira/fields.json` dan dipakai oleh semua perintah berikutnya.

### Sesi berikutnya

```bash
source .venv/bin/activate
```

MCP Playwright aktif otomatis saat Claude Code dibuka di folder ini (konfigurasi di `.mcp.json`).

---

## Cara Menggunakan Agent

Buka Claude Code di folder `myQA/`. Instruksi agent dimuat otomatis dari `CLAUDE.md`. Mulai percakapan dengan menyebut ID tiket Jira.

---

## Alur Kerja

```
[Fase 1]  Fetch → Analisis → Generate AC → Tulis ke Jira → PAUSE
                                                                ↓
                                              [Refine AC] ← opsional, bisa diulang
                                                                ↓
[Fase 2]  Fetch AC final → Generate TS & TC → Tulis ke Jira
```

### Fase 1 — Generate Acceptance Criteria

**Trigger:** Berikan ID tiket Jira.

```
User: PROJ-123
```

Agent akan:
1. Fetch tiket dari Jira (description + AC field yang sudah ada)
2. Analisis requirements — PM vs QA gap analysis jika AC sudah ada
3. Generate atau enrich AC dalam 4 kategori: Functional, Technical, Integration, Data Integrity
4. Tampilkan AC untuk direview
5. Tulis ke Jira dengan **append** (tidak menghapus konten lama)
6. Berhenti dan menunggu

**Output lokal:** `output/[TICKET-ID]/ac.md`

---

### ⏸ Pause — Validasi AC di Jira

Buka tiket di Jira dan edit AC sesuai kebutuhan secara langsung. Setelah selesai, berikan sinyal ke agent.

| Sinyal | Aksi |
|---|---|
| `lanjut` / `generate TS` / `next` | Lanjut ke Fase 2 |
| `refine AC` / `sempurnakan AC` / `perbaiki AC` | Elaborasi AC (lihat bagian Refine AC) |

---

### Refine AC — Opsional

**Trigger:** `refine AC` / `sempurnakan AC` / `elaborasi AC`

Gunakan ini ketika AC sudah divalidasi tapi masih ingin disempurnakan sebelum generate TS. Berbeda dari Fase 1:

| | Fase 1 | Refine AC |
|---|---|---|
| Base | Requirements dari description | AC yang sudah ada di Jira |
| Pendekatan | Generate / Enrich | Elaborasi dan perjelas |
| Write mode | `--append` | **Overwrite** (ganti seluruh AC) |

Agent akan menandai setiap perubahan:
- `[KEPT]` — poin asli tidak diubah
- `[UPDATED]` — poin diperluas atau diperjelas
- `[NEW]` — poin baru dari analisis ulang

Label dihapus sebelum ditulis ke Jira.

Refine bisa diulang lebih dari sekali. Setelah puas, berikan sinyal `lanjut`.

---

### Fase 2 — Generate Test Scenarios & Test Cases

**Trigger:** `lanjut` / `generate TS` / `next`

Agent akan:
1. Fetch ulang AC dari Jira (bukan file lokal — AC di Jira adalah sumber kebenaran)
2. Generate Test Scenarios dari AC
3. Generate Test Cases per TS
4. Tampilkan untuk direview
5. Tulis ke Jira sebagai tabel terstruktur

**Output lokal:** `output/[TICKET-ID]/tc.md`

**Output di Jira:** Tabel dengan kolom:

| Test Scenario | AC | Test Case & Evidence | Priority | Status |
|---|---|---|---|---|
| Judul + Given/When/Then | AC yang di-cover | Daftar TC yang bisa dicentang | MoSCoW | — |

---

## Format Output

### AC (`ac.md`)

```markdown
## Acceptance Criteria

### Functional
- AC-F1: [kriteria]
- AC-F2: [kriteria]

### Technical
- AC-T1: [kriteria]

### Integration
- AC-I1: [kriteria]

### Data Integrity
- AC-D1: [kriteria]
```

### TS & TC (`tc.md`)

```markdown
### TS-01: [Aktor] dapat [melakukan sesuatu]
**AC:** AC-F1, AC-D1
**Priority:** M

**Given**
- [precondition]
**When**
- [langkah konkret 1]
- [langkah konkret 2]
**Then**
- [expected outcome 1]
- [expected outcome 2]

**TC:**
[+] [Aktor] dapat [kondisi valid spesifik]
[-] [Aktor] tidak dapat [kondisi invalid spesifik]
```

**Prefix TC:**
- `[+]` — aktor/sistem **CAN** do something
- `[-]` — aktor/sistem **CANNOT** do something (validasi gagal, fitur tidak tersedia, aksi ditolak)

**Priority (MoSCoW):**
- `M` — Must Have
- `S` — Should Have
- `C` — Could Have
- `W` — Won't Have

---

## Struktur Folder

```
myQA/
├── .claude/
│   ├── settings.local.json       # Permission & config Claude Code
│   └── skills/
│       ├── fetchJira/
│       │   └── SKILL.md          # Skill: fetch tiket dari Jira
│       ├── manageJira/
│       │   └── SKILL.md          # Skill: tulis AC / TC ke Jira
│       ├── generateReport/
│       │   └── SKILL.md          # Skill: generate test execution report
│       └── generatePlaywright/
│           └── SKILL.md          # Skill: generate Playwright automation scripts
├── tools/
│   ├── jira/
│   │   ├── adf_utils.py          # Shared: ADF text extraction + TC table parsing
│   │   ├── get_ticket.py         # Fetch tiket dari Jira
│   │   ├── update_ticket.py      # Tulis AC / TC ke Jira
│   │   ├── discover_fields.py    # Temukan custom field key per project
│   │   ├── list_fields.py        # List semua field di Jira instance
│   │   ├── fields.json           # Mapping field key per project
│   │   └── client.py             # HTTP auth layer
│   ├── playwright/
│   │   ├── parse_adf_tc.py       # Fetch TC dari Jira → parse Functional TS
│   │   └── generate_playwright.py # Generate .spec.ts per Functional TS
│   └── report/
│       └── parse_results.py      # Parse hasil testing dari field TC Jira
├── output/
│   └── [TICKET-ID]/
│       ├── ac.md                 # AC hasil generate
│       ├── tc.md                 # TS & TC hasil generate
│       └── playwright/
│           └── ts-XX-*.spec.ts   # Playwright automation scripts (1 per TS)
├── .mcp.json                     # MCP server config (Playwright)
├── playwright.config.ts          # Playwright test runner config
├── package.json                  # Node.js dependencies
├── CLAUDE.md                     # Instruksi agent (dimuat otomatis)
├── .env                          # Kredensial Jira (tidak di-commit)
└── requirements.txt
```

---

## Menambahkan Project Baru

Jika project belum ada di `fields.json`, agent akan memperingatkan. Jalankan:

```bash
python tools/jira/discover_fields.py PROJ-123 --save
```

Atau untuk melihat semua field yang tersedia dulu:

```bash
python tools/jira/discover_fields.py PROJ-123
```

---

## Troubleshooting

**Field AC atau TC kosong padahal sudah diisi di Jira**
→ Field key belum terpetakan. Jalankan `discover_fields.py PROJ-123 --save`.

**Error saat load `.env`**
→ Pastikan `.env` ada di root folder `myQA/` dan berisi ketiga variabel (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`).

**Dry run untuk preview sebelum kirim ke Jira**
```bash
python tools/jira/update_ticket.py PROJ-123 --ac-file output/PROJ-123/ac.md --dry-run
python tools/jira/update_ticket.py PROJ-123 --tc-table output/PROJ-123/tc.md --dry-run
```
