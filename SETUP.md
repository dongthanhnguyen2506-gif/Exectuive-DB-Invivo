# InVivo Lab — GitHub Actions Setup
## Thời gian cài: ~15 phút | Không cần máy bật 24/7

---

## Bước 1 — Tạo GitHub repo

1. Vào github.com → đăng nhập (hoặc tạo tài khoản miễn phí)
2. Click **"New repository"**
3. Tên: `invivo-dashboard`
4. Chọn **Private**
5. Click **Create repository**

---

## Bước 2 — Upload toàn bộ file lên repo

```
Kéo thả toàn bộ thư mục này vào trang GitHub repo
(hoặc dùng GitHub Desktop nếu quen)
```

Cấu trúc sau khi upload:
```
invivo-dashboard/
├── .github/
│   └── workflows/
│       └── export.yml      ← GitHub Actions config
├── api/
│   └── export.py           ← Script export data
├── public/
│   └── summary_latest.json ← Sẽ tự tạo sau lần chạy đầu
└── SETUP.md
```

---

## Bước 3 — Điền Secrets (QUAN TRỌNG — không hardcode password)

Vào repo GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Thêm lần lượt 6 secrets sau:

| Secret Name   | Giá trị                                      |
|---------------|----------------------------------------------|
| TENANT_ID     | da46fbf7-1825-4f35-b15e-c1c8c11fd769         |
| DATASET_ID    | 10d02dba-bc4e-472f-b4d4-9b9044fb3c4a         |
| PBI_EMAIL     | email đăng nhập Power BI của công ty          |
| PBI_PASS      | mật khẩu Power BI                            |
| VERCEL_TOKEN  | lấy tại vercel.com → Account → Tokens        |
| BLOB_RW_TOKEN | lấy tại Vercel → Storage → Blob → RW Token   |

---

## Bước 4 — Chạy thử thủ công

Vào repo → tab **Actions** → **InVivo — Power BI Export** → **Run workflow** → **Run**

Chờ ~2 phút → xem kết quả:
- ✅ Xanh = thành công
- ❌ Đỏ = có lỗi → click vào xem log → chụp màn hình gửi lại

---

## Bước 5 — Kiểm tra kết quả

Sau khi chạy thành công, file `public/summary_latest.json` sẽ xuất hiện trong repo.
GitHub Actions sẽ tự chạy lại mỗi giờ — không cần làm gì thêm.

---

## Lịch chạy tự động

Script chạy vào đầu mỗi giờ (UTC) = 7h sáng đến 12h đêm giờ VN.
Hoàn toàn tự động, không cần máy tính bật.

