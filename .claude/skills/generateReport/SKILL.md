# generateReport — Test Execution Report Skill

Skill ini membuat test report berdasarkan catatan hasil testing QA yang tersimpan di Jira.
Dipanggil oleh QAanalyst ketika user meminta report dari sebuah tiket.

> **Jira operations** (fetch) ditangani oleh **fetchJira skill** — lihat [SKILL.md](../fetchJira/SKILL.md).
> **Parsing & counting** ditangani oleh `tools/report/parse_results.py`.

---

## Cara Memanggil Skill Ini

Agent lain cukup mendeklarasikan:

```
Gunakan skill generateReport untuk:
- generate report   → generateReport: report [TICKET-ID]
- simpan ke file    → generateReport: report [TICKET-ID] --save output/[TICKET-ID]/report.md
- output JSON       → generateReport: report [TICKET-ID] --json
```

---

## Prasyarat — Format Anotasi Hasil Testing

Sebelum report dapat dibuat, QA tester harus menambahkan anotasi hasil pada setiap TC
di field **Test Case** Jira. Tambahkan field `**Result:**` setelah `**Expected Result:**`:

```
### TC-01: [Test Case Name]
**Scenario:** TS-01
**Type:** Positive
**Preconditions:** ...
**Steps:**
1. ...
**Expected Result:** ...
**Result:** PASS

---

### TC-02: [Test Case Name]
...
**Expected Result:** ...
**Result:** FAIL
**Notes:** [deskripsi masalah yang ditemukan]
```

### Status yang Valid

| Status | Alias | Keterangan |
|---|---|---|
| `PASS` | `LULUS` | Test berhasil |
| `FAIL` | `GAGAL` | Test gagal — wajib tambahkan `**Notes:**` |
| `BLOCKED` | `BLOKIR` | Tidak dapat dijalankan karena blocker |
| `SKIP` | | Sengaja dilewati di iterasi ini |
| _(tidak ada Result)_ | | **PENDING** — belum dieksekusi |

Alternatif: tambahkan emoji langsung di header TC:
- `### TC-01: Nama Test ✅` → PASS
- `### TC-02: Nama Test ❌` → FAIL
- `### TC-03: Nama Test 🚫` → BLOCKED

---

## Workflow

### Step 1 — Cek Kesiapan Tiket

**Panggil skill fetchJira: fetch [TICKET-ID]**

Dari output, verifikasi:

| Kondisi | Tindakan |
|---|---|
| Field `Test Case` kosong | Ingatkan user: TC belum dibuat. Jalankan QAanalyst terlebih dahulu untuk generate dan upload TC. |
| TC ada tapi tidak ada `**Result:**` | Lanjut — report akan tampil dengan semua status **PENDING**. Ingatkan user untuk menambahkan anotasi. |
| TC ada dan sudah dianotasi | Lanjut ke Step 2. |

---

### Step 2 — Parse Hasil Testing

Jalankan tool parse_results dari root project (`myQA/`):

```bash
# Output Markdown report (default)
python tools/report/parse_results.py PROJ-123

# Output JSON untuk diproses lebih lanjut
python tools/report/parse_results.py PROJ-123 --json
```

Tool ini akan otomatis:
- Fetch tiket dari Jira menggunakan konfigurasi `.env` dan `fields.json`
- Ekstrak semua TS (Test Scenario) dari field Test Case
- Ekstrak semua TC (Test Case) beserta status-nya
- Hitung metrics: total TS, TC, passed, failed, blocked, skip, pending
- Hitung **pass rate** dari TC yang sudah dieksekusi (total − pending − skip)
- Sertakan konten `qa_feedback` field sebagai QA Notes

---

### Step 3 — Tampilkan dan Simpan Report

Tampilkan output report kepada user.

Untuk menyimpan ke file:

```bash
python tools/report/parse_results.py PROJ-123 --save output/PROJ-123/report.md
```

Direktori `output/PROJ-123/` akan dibuat otomatis jika belum ada.

---

## Format Report yang Dihasilkan

```
# Test Execution Report — PROJ-123

**Feature:** [judul tiket]
**Ticket:** [URL tiket Jira]
**Status:** [status tiket]
**Assignee:** [nama assignee]
**Report Date:** [tanggal hari ini]

---

## Summary

| Metric | Value |
|---|---|
| Test Scenarios | N |
| Test Cases | N |
| ✅ Passed | N |
| ❌ Failed | N |
| 🚫 Blocked | N |
| ⏭ Skipped | N |
| ⏳ Pending | N |
| **Pass Rate** | **X%** |

---

## Status per Test Scenario

[tabel breakdown per TS: total TC, jumlah per status]

---

## Test Case Results

[tabel semua TC: ID, nama, scenario, status]

---

## Issues Found

[detail TC yang FAIL atau BLOCKED beserta Notes-nya]

---

## QA Notes

[konten field QA Feedback dari Jira, jika ada]
```

---

## Behavior Guidelines

- Jika `test_case` field kosong → ingatkan user untuk generate TC via QAanalyst dulu, lalu upload ke Jira.
- Jika tidak ada TC yang dianotasi → tampilkan report (semua PENDING) dan ingatkan user menambahkan `**Result:**`.
- Jika ada TC yang FAIL atau BLOCKED → tanyakan apakah notes perlu dicatat ke field `qa_feedback` Jira.
- Pass rate dihitung dari TC yang sudah **dieksekusi** (total − pending − skip), bukan dari total keseluruhan.
- Selalu sebutkan tanggal report saat menyajikan hasilnya kepada user.
