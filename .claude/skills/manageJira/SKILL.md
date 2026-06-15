# manageJira — Jira Write Skill

Skill ini menangani semua operasi **write** ke Jira: update Acceptance Criteria (AC) dan Test Cases (TC).
Untuk fetch tiket, gunakan skill **fetchJira** — lihat [SKILL.md](../fetchJira/SKILL.md).

---

## Cara Memanggil Skill Ini

```
manageJira: write-ac [TICKET-ID] [file]
manageJira: write-tc [TICKET-ID] [file]
```

---

## Operasi yang Tersedia

### 1. Update Acceptance Criteria (AC) ke Jira

```bash
# Append — tambahkan di bawah AC yang sudah ada (digunakan di Phase 1)
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --ac-file output/PROJ-123/ac.md --append --yes

# Overwrite — timpa seluruh AC field (digunakan di Refine AC)
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --ac-file output/PROJ-123/ac.md --yes

# Dry run — preview payload tanpa kirim
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --ac-file output/PROJ-123/ac.md --dry-run
```

---

### 2. Update Test Cases (TC) ke Jira — Format Tabel (Direkomendasikan)

Satu file `tc.md` berisi semua TS dengan TC inline, di-render sebagai ADF table di Jira.

```bash
# Tulis sebagai ADF table
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --tc-table output/PROJ-123/tc.md --yes

# Dry run
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --tc-table output/PROJ-123/tc.md --dry-run
```

Format `tc.md` yang diharapkan oleh `--tc-table`:

```
### TS-01: [Journey Name]
**Type:** Functional
**Priority:** M

**Given**
- [precondition]
**When**
- [step 1]
- [step 2]
**Then**
- [outcome 1]

**TC:**
[+] Positive test case title
[-] Negative test case title

---

### TS-02: ...
```

Table yang dihasilkan di Jira memiliki kolom: **Test Scenario | Type | Test Case & Evidence | Priority | Status**, dengan nomor baris otomatis dan TC sebagai checkable task items.

### 2b. Update Test Cases (TC) ke Jira — Format Plain (Legacy)

```bash
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --tc-file tc.md --yes
```

---

### 3. Update AC dan TC Sekaligus

```bash
source .venv/bin/activate && python tools/jira/update_ticket.py PROJ-123 --ac-file output/PROJ-123/ac.md --tc-table output/PROJ-123/tc.md --yes
```

---

## Scripts Reference

| Script | Fungsi |
|---|---|
| `update_ticket.py` | Write AC dan/atau TC ke Jira |
| `discover_fields.py` | Temukan dan simpan custom field key per project ke `fields.json` |
| `client.py` | Auth & HTTP layer (internal) |

**Config files:**

| File | Fungsi |
|---|---|
| `.env` | Kredensial Jira (URL, email, API token) |
| `tools/jira/fields.json` | Mapping custom field key per project |

Dokumentasi lengkap: [tools/jira/jira-tools.md](../../tools/jira/jira-tools.md).

---

## Behavior

- Selalu gunakan `--yes` untuk skip konfirmasi interaktif (Claude tidak bisa menjawab prompt interaktif).
- Gunakan `--append` di Phase 1 — jangan timpa AC yang sudah ada.
- Gunakan overwrite (tanpa `--append`) hanya di Refine AC.
- Sebelum write TC, cek dulu apakah field Test Case sudah berisi konten via fetchJira. Jika sudah ada isinya, tanyakan user.
- Jika field key tidak ditemukan untuk sebuah project, jalankan `discover_fields.py TICKET-ID --save`.
- Input Markdown otomatis dikonversi ke Atlassian Document Format (ADF) sebelum dikirim ke Jira.
