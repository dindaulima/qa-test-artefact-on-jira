# generatePlaywright — Playwright Automation Script Generator Skill

Skill ini menghasilkan Playwright TypeScript spec files dari TC Functional di Jira.

**Source of truth: Jira** — skill ini selalu fetch dari Jira, bukan dari file lokal.

**Struktur output:**
- 1 TS Functional = 1 file `.spec.ts`
- 1 TC dalam TS = 1 blok `test()` di file tersebut
- TC title digunakan langsung (sudah atomic dan self-descriptive)

---

## Cara Memanggil Skill Ini

```
generatePlaywright: generate [TICKET-ID]
generatePlaywright: generate [TICKET-ID] --out-dir tests/e2e/
```

---

## Prasyarat

Field **Test Case** di tiket Jira harus sudah berisi data (Phase 2b selesai dan TC sudah ditulis ke Jira).
Jika belum ada → arahkan user ke Phase 2b terlebih dahulu.

---

## Workflow

### Step 1 — Preview Functional TCs dari Jira

```bash
source .venv/bin/activate && python tools/playwright/parse_adf_tc.py [TICKET-ID]
```

Tampilkan output ke user. Jika tidak ada Functional TS → informasikan dan tanyakan apakah user ingin lihat semua tipe:

```bash
source .venv/bin/activate && python tools/playwright/parse_adf_tc.py [TICKET-ID] --all-types
```

**STOP** — tunggu konfirmasi user sebelum generate.

---

### Step 2 — Generate Playwright scripts

```bash
source .venv/bin/activate && python tools/playwright/generate_playwright.py [TICKET-ID]
```

Dengan custom output dir:
```bash
source .venv/bin/activate && python tools/playwright/generate_playwright.py [TICKET-ID] --out-dir tests/e2e/
```

---

### Step 3 — Tampilkan hasil ke user

- Jumlah file `.spec.ts` yang dihasilkan
- Daftar path file
- Reminder: setiap file adalah skeleton dengan `TODO` placeholder — implementasi akan ditambahkan di langkah berikutnya

---

## Format File yang Dihasilkan

**Nama file:** `{ts-id}-{ts-title-slug}.spec.ts`

Contoh: `ts-01-admin-dapat-membuat-voucher-baru.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

// TS-01: Admin dapat membuat voucher baru
// Type: Functional | Priority: M

test('[-] Admin tidak bisa mengosongkan nama voucher', async ({ page }) => {
  // TODO: implement
  expect(true).toBe(true);
});

test('[+] Admin dapat membuat voucher dengan data valid', async ({ page }) => {
  // TODO: implement
  expect(true).toBe(true);
});
```

---

## Tools Reference

| Script | Fungsi |
|---|---|
| `tools/jira/adf_utils.py` | **Shared** — ADF text extraction + TC table parsing (digunakan oleh semua skill) |
| `tools/playwright/parse_adf_tc.py` | Fetch dari Jira → parse via adf_utils → tampilkan summary |
| `tools/playwright/generate_playwright.py` | Generate `.spec.ts` per TS Functional |

---

## Behavior Guidelines

- Selalu preview Functional TCs (Step 1) sebelum generate.
- Jika Test Case field kosong → arahkan ke Phase 2b.
- Jika tidak ada Functional TS → informasikan, tanyakan apakah ingin lihat tipe lain.
- Setiap file adalah skeleton — sampaikan ke user bahwa implementasi ditambahkan terpisah.
- Output default: `output/[TICKET-ID]/playwright/`
