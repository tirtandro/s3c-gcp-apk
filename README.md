# 🌿 S3C — Smart Sustainable School Canteen

Platform digital untuk transformasi kantin sekolah menjadi ekosistem yang lebih cerdas, sehat, dan berkelanjutan.

---

## 🚀 Fitur Utama & Deployment

- **Cloud Native**: Berjalan di Google Cloud Run & Cloud SQL (PostgreSQL).
- **Android Ready**: Berupa Progressive Web App (PWA) yang dapat diinstal langsung dari browser.
- **Automated APK**: Build otomatis via GitHub Actions menggunakan Bubblewrap.

## 🔑 Akun Demo

| Role | Username | Password |
|------|----------|----------|
| 🎓 Murid | `andi` | `student123` |
| 🎓 Murid 2 | `siti` | `student123` |
| 🍽️ Tenant 1 | `tenant1` | `tenant123` |
| 🍽️ Tenant 2 | `tenant2` | `tenant123` |

*(Login Admin dirahasiakan untuk alasan keamanan)*

---

## 📱 Fitur Lengkap

### 🎓 Role Murid (Student)
- **Dashboard** — Poin eco-warrior, level gamifikasi, ringkasan aktivitas.
- **Katalog Menu** — Filter kategori & pencarian, modal info gizi lengkap, label Menu Sehat.
- **Digital Order** — Keranjang belanja interaktif, multi-tenant, catatan pesanan.
- **PWA Install** — Bisa diinstal sebagai aplikasi Android tanpa Play Store.

### 🍽️ Role Tenant (Pengelola Kantin)
- **Dashboard** — Pendapatan harian, pesanan pending, aktivitas terbaru.
- **Manajemen Menu** — CRUD menu, input nilai gizi detail, toggle aktif/nonaktif.
- **Manajemen Pesanan** — Lihat & update status pesanan.

### ⚙️ Role Admin (Tim S3C)
- **Dashboard** — Statistik global, analitik tren, & distribusi food waste.
- **Kelola Edukasi** — Manajemen artikel gizi & lingkungan secara dinamis (CRUD).
- **Marketplace** — Kelola produk daur ulang dari sisa kantin.

---

## 📁 Struktur Proyek Terbaru

```
S3C-Flask/
├── app.py                    ← Aplikasi utama Flask
├── requirements.txt
├── cloudbuild.yaml           ← Konfigurasi Deploy GCP
├── .github/
│   └── workflows/
│       └── android_apk.yml   ← Auto-Build APK via GitHub Actions
├── android/
│   └── twa-manifest.json     ← Konfigurasi PWA to Android
├── static/
│   ├── manifest.json         ← PWA Identity
│   ├── sw.js                 ← Service Worker
│   └── img/
│       └── logo_sekolah.png  ← Ikon Aplikasi
└── templates/                ← Jinja2 Templates
```

---

## 🎨 Teknologi

- **Backend**: Python + Flask + PostgreSQL
- **Frontend**: HTML5 + CSS3 + Vanilla JS (Mobile First)
- **Android**: Trusted Web Activity (TWA) / Bubblewrap
- **Infrastructure**: Google Cloud Platform (Cloud Run, Cloud SQL)
