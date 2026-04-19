# 🌿 S3C — Smart Sustainable School Canteen

Platform digital untuk transformasi kantin sekolah menjadi ekosistem yang lebih cerdas, sehat, dan berkelanjutan.

---

## 🚀 Fitur Utama & Deployment

- **Cloud Native**: Berjalan di Google Cloud Run & Cloud SQL (PostgreSQL).
- **Android Ready**: Berupa Progressive Web App (PWA) yang dapat diinstal langsung dari browser.
- **Native APK Build**: Pembuatan APK menggunakan sistem Gradle TWA (Trusted Web Activity) asli untuk stabilitas tinggi.
- **Automated CI/CD**: Build APK otomatis via GitHub Actions setiap kali ada perubahan kode.

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
- **Katalog Menu** — Filter kategori & pencarian, informasi gizi lengkap.
- **Digital Order** — Keranjang belanja interaktif, multi-tenant.
- **Notifikasi Pintar** — Notifikasi push & in-app update status pesanan yang interaktif.
- **PWA Install** — Bisa diinstal langsung dari Chrome Android.

### 🍽️ Role Tenant (Pengelola Kantin)
- **Dashboard** — Pendapatan harian dan pesanan masuk.
- **Manajemen Menu** — CRUD menu dengan input nilai gizi detail.
- **Manajemen Pesanan** — Update status pesanan secara real-time.
- **Notifikasi Real-time** — Pemberitahuan instan saat ada pesanan baru masuk.

### ⚙️ Role Admin (Tim S3C)
- **Dashboard** — Statistik global dan analitik tren kantin.
- **Kelola Edukasi** — Manajemen artikel gizi & lingkungan (CRUD).
- **Marketplace** — Kelola produk hasil daur ulang limbah kantin.

---

## 📁 Struktur Proyek

```
S3C-Flask/
├── app.py                    ← Backend utama (Flask)
├── .github/
│   └── workflows/
│       └── android_apk.yml   ← Pipeline Otomatisasi APK
├── android/                  ← Project Android Native (TWA)
│   ├── app/src/main/         ← Manifest & Resources (Ikon otomatis)
│   └── build.gradle          ← Konfigurasi Gradle
├── static/
│   ├── manifest.json         ← Identitas PWA
│   └── sw.js                 ← Service Worker
└── templates/                ← Tampilan (Jinja2)
```

---

## 🎨 Teknologi & Infrastruktur

- **Backend**: Python, Flask, PostgreSQL
- **Android**: Android Browser Helper (Trusted Web Activity)
- **DevOps**: GitHub Actions, Docker, Google Cloud Build
- **Cloud**: Google Cloud Run (Compute), Cloud SQL (Database)
