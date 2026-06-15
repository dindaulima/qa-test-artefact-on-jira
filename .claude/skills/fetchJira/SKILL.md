# fetchJira — Fetch Jira Ticket Skill

Skill ini mengambil data tiket Jira beserta semua field yang relevan untuk analisis QA.
Dipanggil di awal setiap fase (Phase 1, Refine AC, Phase 2) sebelum melakukan analisis atau generate artefak.

---

## Cara Memanggil Skill Ini

```
fetchJira: fetch [TICKET-ID]
fetchJira: fetch [TICKET-ID] --json
```

---

## Commands

```bash
# Human-readable output (default — untuk analisis)
source .venv/bin/activate && python tools/jira/get_ticket.py PROJ-123

# JSON output (untuk parsing field tertentu)
source .venv/bin/activate && python tools/jira/get_ticket.py PROJ-123 --json

# Tambah field custom tertentu
source .venv/bin/activate && python tools/jira/get_ticket.py PROJ-123 --fields customfield_10200,customfield_10300
```

---

## Data yang Dikembalikan

| Field | Keterangan |
|---|---|
| `key` | ID tiket (e.g. PROJ-123) |
| `summary` | Judul tiket |
| `type` | Tipe issue (Story, Bug, Task, dll.) |
| `status` | Status tiket |
| `priority` | Prioritas |
| `reporter` / `assignee` | Nama orang |
| `description` | Deskripsi / requirements dari PM (ADF → plain text) |
| `acceptance_criteria` | AC yang sudah ada di Jira (QA field) — kosong jika belum diisi |
| `test_case` | Isi field Test Case — digunakan untuk cek apakah sudah ada konten sebelum menulis |
| `linked_tickets` | Tiket yang terhubung (parent, dependencies) |
| `subtasks` | Daftar sub-task |
| `comments` | Komentar yang relevan |

---

## Cara Membaca Output

Setelah fetch, pisahkan dua sumber yang berbeda:

- **`description`** — konten dari PM: requirements, konteks bisnis, AC versi PM (jika ada)
- **`acceptance_criteria`** — AC yang ditulis oleh QA di field dedicated

Jangan gabungkan keduanya. Keduanya dianalisis secara terpisah di Layer B (AC Source Conditions).

Untuk cek apakah field Test Case sudah berisi konten, lihat nilai `test_case` di output:
- Kosong / `null` → aman untuk ditulis
- Ada isinya → tanyakan user sebelum overwrite

---

## Setup (one-time)

Jalankan dari root project (`myQA/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Isi `.env` dengan kredensial Jira:

```
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

Untuk sesi berikutnya cukup:

```bash
source .venv/bin/activate
```

---

## Custom Field Setup (per project baru)

Setiap Jira project punya custom field key yang berbeda. Jalankan sekali per project baru:

```bash
# Auto-detect dan simpan mapping ke fields.json
source .venv/bin/activate && python tools/jira/discover_fields.py PROJ-123 --save

# Cari field spesifik
source .venv/bin/activate && python tools/jira/discover_fields.py PROJ-123 --search "test case"
```

Mapping disimpan di `tools/jira/fields.json` dan dimuat otomatis oleh semua script.

---

## Behavior

- Jika project belum ada di `fields.json`, jalankan `discover_fields.py TICKET-ID --save` terlebih dahulu.
- Gunakan output `--json` hanya jika perlu parsing field tertentu. Untuk analisis AC/requirements, gunakan output default (human-readable).
