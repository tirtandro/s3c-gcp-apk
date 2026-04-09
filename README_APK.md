# Panduan Pembuatan APK S3C (Metode Bubblewrap)

Dokumen ini menjelaskan cara mengubah website S3C Anda menjadi file **.APK** yang siap diinstal di HP Android menggunakan alat resmi Google bernama **Bubblewrap**.

## 1. Persiapan Lingkungan (Sekali Saja)
Sebelum memulai, pastikan komputer Anda sudah terpasang:
1.  **Node.js (LTS)**: Unduh di [nodejs.org](https://nodejs.org/)
2.  **Java JDK 11+**: Unduh di [Adoptium](https://adoptium.net/)

## 2. Instalasi Alat Bubblewrap
Buka Terminal atau PowerShell, lalu jalankan perintah:
```bash
npm install -g @bubblewrap/cli
```

## 3. Inisialisasi Project APK
Gunakan URL website S3C Anda yang sudah ada di Cloud Run (Ganti `[URL-S3C-ANDA]` dengan link aslinya):
```bash
bubblewrap init --manifest=https://[URL-S3C-ANDA]/manifest.json
```
*   **Penting**: Saat ditanya lokasi JDK atau Android SDK, tekan **Enter** saja jika Bubblewrap berhasil menemukannya secara otomatis.
*   Bubblewrap akan mengunduh aset dan mengatur identitas aplikasi berdasarkan file `manifest.json` yang sudah kita buat sebelumnya.

## 4. Membuat Kunci Keamanan (Signing Key)
Android mewajibkan setiap aplikasi memiliki kunci tanda tangan digital. Jika Anda belum punya, Bubblewrap akan menawarkan untuk membuatnya:
```bash
bubblewrap build
```
*   Ikuti instruksi pembuatan password untuk **Keystore**.
*   **SIMPAN BAIK-BAIK** file Keystore tersebut dan password-nya. File ini dibutuhkan jika Anda ingin melakukan update aplikasi di masa depan.

## 5. Hasil Akhir
Setelah proses `build` selesai, Anda akan mendapatkan file:
`app-release-signed.apk`

### Cara Instalasi di HP:
1.  Kirim file `.apk` tersebut ke HP (via WhatsApp, Google Drive, atau Kabel Data).
2.  Klik file tersebut di HP.
3.  Jika muncul peringatan "Blocked by Play Protect", klik **"Install Anyway"** (ini muncul karena aplikasi belum didaftarkan resmi ke Google Play Store).
4.  Selesai! Aplikasi S3C akan muncul di daftar aplikasi HP Anda.

---
**Tips:** Jika Anda mengubah warna tema atau ikon di website, Anda hanya perlu menjalankan `bubblewrap build` lagi untuk memperbarui APK-nya.
