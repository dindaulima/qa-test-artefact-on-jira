---
name: Aturan write AC dan TC ke Jira
description: AC selalu --append tanpa tanya. TC/TS hanya ditulis jika field Test Case di Jira kosong.
type: feedback
---

**AC:** Selalu gunakan `--append` saat menulis AC ke Jira. Tidak perlu tanya konfirmasi mode.

**TC/TS:** Hanya tulis ke Jira jika field Test Case di tiket **kosong**. Jika sudah ada isinya, jangan tulis — cukup tampilkan hasil generate di conversation.

**Why:** User lebih mudah validasi AC langsung di Jira. TC yang sudah ada di Jira dianggap sudah valid dan tidak boleh ditimpa tanpa keputusan eksplisit user.

**How to apply:**
- `update_ticket.py ... --ac-file ... --append` → selalu untuk AC
- Sebelum write TC: cek field `test_case` dari hasil `get_ticket.py`. Jika kosong, langsung tulis. Jika tidak kosong, informasikan ke user dan tanyakan apakah mau ditimpa atau tidak.
