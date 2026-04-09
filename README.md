# 🌿 S3C — Smart Sustainable School Canteen

Platform digital untuk transformasi kantin sekolah menjadi ekosistem yang lebih cerdas, sehat, dan berkelanjutan.

---

## 🚀 Cara Menjalankan

### Prasyarat
- Python 3.8+
- Flask (`pip install flask`)

### Langkah-langkah

```bash
# 1. Clone / extract project
cd s3c

# 2. Install dependency
pip install flask

# 3. Jalankan aplikasi
python3 app.py

# 4. Buka browser
# http://localhost:5000
```

---

## 🔑 Akun Demo

| Role | Username | Password |
|------|----------|----------|
| 🎓 Murid | `andi` | `student123` |
| 🎓 Murid 2 | `siti` | `student123` |
| 🍽️ Tenant 1 | `tenant1` | `tenant123` |
| 🍽️ Tenant 2 | `tenant2` | `tenant123` |
| ⚙️ Admin | `admin` | `admin123` |

---

## 📱 Fitur Lengkap

### 🎓 Role Murid (Student)
- **Dashboard** — Poin eco-warrior, level gamifikasi, ringkasan aktivitas
- **Katalog Menu** — Filter kategori & pencarian, modal info gizi lengkap, label Menu Sehat
- **Digital Order** — Keranjang belanja interaktif, multi-tenant, catatan pesanan
- **Food Waste Log** — Gamifikasi sisa makanan, sistem poin, riwayat log
- **Pojok Edukasi** — Artikel gizi & lingkungan, filter kategori, halaman detail
- **Marketplace** — Lihat produk daur ulang dari sisa kantin

### 🍽️ Role Tenant (Pengelola Kantin)
- **Dashboard** — Pendapatan harian, pesanan pending, aktivitas terbaru
- **Manajemen Menu** — CRUD menu, emoji picker, input nilai gizi detail, toggle aktif/nonaktif
- **Manajemen Pesanan** — Lihat & update status pesanan (pending → diproses → siap → selesai), statistik menu terlaris

### ⚙️ Role Admin (Tim S3C)
- **Dashboard** — Statistik global: murid, pesanan, waste logs, marketplace
- **Analitik** — Chart tren pesanan 7 hari, distribusi food waste (donut chart), rasio menu sehat, performa tenant
- **Marketplace Limbah** — CRUD produk hasil daur ulang (kompos, pupuk cair, kerajinan)
- **Kelola Edukasi** — Publikasi & hapus artikel gizi & lingkungan

---

## 🗄️ Struktur Database

```
users          → id, name, username, password, role, kelas, tenant_name
menus          → id, tenant_id, name, description, price, category,
                 calories, protein, carbs, fat, fiber, is_healthy, is_available
orders         → id, student_id, tenant_id, status, total_price, notes
order_items    → id, order_id, menu_id, quantity, subtotal
waste_logs     → id, student_id, menu_id, waste_level, waste_reason, points_earned
education_posts→ id, title, content, category, image_emoji, author_id
marketplace_items → id, name, description, category, price, unit, stock, image_emoji
```

---

## 🎨 Desain & Teknologi

- **Backend**: Python + Flask + SQLite3 (tanpa ORM eksternal)
- **Frontend**: HTML5 + CSS3 + Vanilla JS, mobile-first
- **Charts**: Chart.js (CDN)
- **Icons**: Font Awesome 6 (CDN)
- **Fonts**: Plus Jakarta Sans + Fraunces (Google Fonts)
- **Palet Warna**: Forest Green (#1a5c38), Leaf (#2d8653), Earth (#8b6914), Cream (#fdfaf6)

---

## 📁 Struktur Folder

```
s3c/
├── app.py                    ← Aplikasi utama Flask
├── requirements.txt
├── README.md
├── instance/
│   └── s3c.db                ← SQLite database (auto-created)
└── templates/
    ├── base.html             ← Layout utama (nav, flash, bottom nav)
    ├── landing.html          ← Halaman beranda publik
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── student/
    │   ├── dashboard.html
    │   ├── menu_catalog.html
    │   ├── order.html
    │   ├── my_orders.html
    │   ├── waste_log.html
    │   ├── education.html
    │   ├── education_detail.html
    │   └── marketplace.html
    ├── tenant/
    │   ├── dashboard.html
    │   ├── menus.html
    │   ├── menu_form.html
    │   └── orders.html
    └── admin/
        ├── dashboard.html
        ├── analytics.html
        ├── marketplace.html
        ├── marketplace_form.html
        └── education.html
```
