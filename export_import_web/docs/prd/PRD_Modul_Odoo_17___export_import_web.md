# PRD Modul Odoo 17: Export & Import Web

**Nama teknis modul:** `export_import_web` **Versi target:** Odoo 17.0 (Community & Enterprise) **Author:** Arif N Ramadhan **Perusahaan:** PT Niits Inovasi Teknologi **Lisensi:** OPL-1 **Harga:** USD 27,56 **Status dokumen:** Draft v2.1 (cakupan: website bawaan Odoo + blog, event, eCommerce)

## 1. Ringkasan

**Export & Import Web** adalah modul Odoo 17 untuk **membackup dan merestore website bawaan Odoo** (modul `website`) ke dalam satu file ZIP: halaman, menu, kustomisasi tampilan, dan media. Pengguna cukup klik **Backup** untuk mengunduh ZIP, lalu **Restore** untuk mengembalikannya di instance yang sama atau di instance Odoo lain.

ZIP memuat data website dalam format JSON terstruktur plus file media, lengkap dengan `manifest.json` berisi versi Odoo, daftar modul, dan checksum. Saat restore, modul memvalidasi paket, menyamakan referensi ID antar-record, lalu menulis ulang data website.

Modul ini **tidak** meng-host website static dari ZIP. Cakupannya: backup dan restore satu atau beberapa website Odoo dalam satu ZIP, termasuk konten blog, event, dan katalog eCommerce bila modulnya terpasang. Backup dan restore hanya antar instance dengan versi Odoo yang sama, dan ZIP diunduh manual tanpa storage eksternal.

## 2. Tujuan & Non-Tujuan

### Tujuan

1. Backup satu atau beberapa website Odoo sekaligus (halaman, menu, view kustom, asset, media) menjadi satu ZIP dengan satu klik.
2. Ikut membackup konten modul blog, event, dan katalog eCommerce (produk, kategori, atribut, gambar) bila modulnya terpasang.
3. Restore dari ZIP ke website yang sama (Replace) atau sebagai website baru (Create New), dengan pemetaan website per website.
4. Restore tetap konsisten: referensi antar-record dan URL media otomatis disesuaikan.
5. Validasi dan pratinjau paket sebelum data diubah, plus snapshot otomatis sebagai jaring pengaman.
6. UI bersih dan rapi di bawah menu **Technical**; backup diunduh manual sebagai file `.zip`.

### Non-Tujuan (v1.0)

- Hosting website static dari ZIP (HTML/CSS/JS).
- Data transaksional: pesanan, pembayaran, pelanggan, stok, pendaftar event, komentar blog, hasil form.
- Backup database atau filestore Odoo secara keseluruhan.
- Restore lintas versi Odoo; versi di paket dan di tujuan harus sama (17.0).
- Backup terjadwal otomatis dan penyimpanan ke storage eksternal (SFTP, S3). Backup hanya dibuat manual dan diunduh sebagai ZIP.

## 3. Metadata Modul & Menu

Modul bergantung pada `website` karena yang dibackup adalah data website Odoo.

| Field `__manifest__.py` | Nilai |
| --- | --- |
| name | Export & Import Web |
| technical name | `export_import_web` |
| version | 17.0.1.0.0 |
| category | Website / Technical |
| summary | Backup & restore Odoo website (pages, menus, media, blog, events, shop) via ZIP |
| author | Arif N Ramadhan |
| maintainer | PT Niits Inovasi Teknologi |
| license | OPL-1 |
| price / currency | 27.56 / USD |
| depends | `base`, `web`, `mail`, `website` |
| dependensi opsional (dideteksi saat runtime, bukan hard depend) | `website_blog`, `website_event`, `website_sale` |
| application / installable | False / True |

Menu berada di **Settings → Technical** (mode developer aktif), parent `base.menu_custom`:

```
Settings
└── Technical
    └── Export & Import Web
        ├── Backups     (riwayat dan unduhan)
        ├── Restore     (wizard restore dari ZIP)
        └── Configuration
```

Menu hanya terlihat oleh grup **Export Import Web / Manager** dan **Administrator** (`base.group_system`).

## 4. Data yang Dibackup

Cakupan v1.0 mencakup data website (`website_id`) yang dipilih, baik satu maupun beberapa website, ditambah konten modul opsional yang terpasang.

| Data | Model Odoo | Isi yang dibackup | Perlakuan saat restore |
| --- | --- | --- | --- |
| Website | `website` | Nama, domain, bahasa, setelan SEO dasar | Update (Replace) atau buat baru; domain tidak ditimpa tanpa konfirmasi |
| Halaman | `website.page` | URL, nama, publish, SEO, menu | Dicocokkan berdasar `url`; buat atau update |
| View halaman & kustom | `ir.ui.view` | `arch_db`, `key`, `inherit_id`, `active`, `priority` | Dicocokkan berdasar `key`; `inherit_id` di-remap |
| Menu | `website.menu` | Hierarki, nama, URL, urutan | Dibangun ulang sesuai pohon |
| Redirect | `website.rewrite` | Pola URL lama dan baru | Buat atau update |
| Asset kustom | `ir.asset` | SCSS/JS kustom hasil editor | Dicocokkan berdasar `name` |
| Media | `ir.attachment` | File (gambar, dokumen) dan metadata publik | Diunggah ulang; URL `/web/image/<id>` ditulis ulang |
| Terjemahan | Field JSON pada record di atas | Teks per bahasa | Ikut tertulis bersama record |
| Blog (butuh `website_blog`) | `blog.blog`, `blog.post`, `blog.tag`, `blog.tag.category` | Blog, artikel (konten, cover, tag, tanggal, status publish), terjemahan | Dicocokkan berdasar slug; komentar tidak ikut |
| Event (butuh `website_event`) | `event.event`, `event.type`, `event.tag`, `event.event.ticket` | Definisi event, tiket, tag, konten halaman event, tanggal, lokasi | Dicocokkan berdasar nama dan tanggal mulai; pendaftar (`event.registration`) tidak ikut |
| Katalog eCommerce (butuh `website_sale`) | `product.template`, `product.product`, `product.public.category`, `product.attribute`, `product.template.image` | Produk terpublikasi, varian, atribut, kategori publik, gambar, deskripsi eCommerce, harga jual | Produk dicocokkan berdasar `default_code`, lalu nama; kategori internal, UoM, dan pajak dicocokkan berdasar nama, bila tidak ada dipakai default dan dicatat sebagai peringatan |

Di luar cakupan: view dan data bawaan modul (tidak diubah); data transaksional (pesanan, pendaftar event, komentar blog, pelanggan, stok, pricelist pelanggan, akun akuntansi produk); konten modul lain di luar tiga modul di atas. Kelompok konten modul hanya muncul bila modulnya terpasang, dan restore mensyaratkan modul yang sama terpasang di tujuan.

## 5. Fitur Fungsional

### 5.1 Backup

| ID | Kebutuhan | Prioritas |
| --- | --- | --- |
| FR-01 | Pilih satu atau beberapa website (multi-website) lalu klik **Backup**; semuanya masuk satu ZIP | Must |
| FR-02 | Pilihan isi backup per kelompok: Halaman & view, Menu & redirect, Asset kustom, Media, Blog, Event, Katalog eCommerce (kelompok modul hanya tampil bila modulnya terpasang) | Must |
| FR-03 | ZIP berisi JSON per website, folder media bersama, dan `manifest.json` | Must |
| FR-04 | Nama file otomatis: `backup_<website>_YYYYMMDD_HHMMSS.zip` (multi-website: `backup_multi_...`) | Must |
| FR-05 | Riwayat backup tersimpan (nama, website, ukuran, checksum, pembuat, tanggal) dan bisa diunduh ulang | Must |
| FR-06 | Hapus backup manual dan retensi maksimum per website | Should |
| FR-07 | Unduhan langsung di browser setelah backup selesai; tidak ada penyimpanan ke storage eksternal dan tidak ada jadwal otomatis | Must |

### 5.2 Restore

| ID | Kebutuhan | Prioritas |
| --- | --- | --- |
| FR-10 | Wizard Restore: upload ZIP lalu validasi otomatis | Must |
| FR-11 | Validasi: struktur ZIP, `manifest.json`, checksum SHA-256, versi Odoo **sama persis** (17.0), modul yang dibutuhkan terpasang. Bila modul kelompok terpilih belum terpasang, restore diblokir sampai pengguna membatalkan centang kelompok tersebut | Must |
| FR-12 | Pratinjau: daftar website dalam paket, jumlah halaman/view/menu/media/artikel/event/produk, ukuran, tanggal backup, peringatan | Must |
| FR-13 | Per website dalam paket, pilih mode **Replace** (timpa website tujuan yang dipilih) atau **Create New** (buat website baru) | Must |
| FR-14 | Pilih website dan kelompok data mana yang direstore (misalnya hanya Media atau hanya Blog) | Should |
| FR-15 | Snapshot otomatis website tujuan sebelum Replace (default aktif) | Must |
| FR-16 | Restore atomik: gagal di tengah berarti rollback, data lama utuh | Must |
| FR-17 | Restore langsung dari riwayat backup | Should |
| FR-18 | Laporan hasil: jumlah record dibuat/diupdate/dilewati dan daftar peringatan | Must |

### 5.3 Pengaturan

| Parameter | Default |
| --- | --- |
| Ukuran maksimum ZIP upload | 200 MB (dapat diubah di Configuration) |
| Ukuran maksimum setelah ekstrak | 1 GB (dapat diubah di Configuration) |
| Retensi backup manual per website | 5 (0 = tanpa batas) |
| Retensi snapshot otomatis per website | 3 (terpisah dari retensi backup manual) |
| Snapshot sebelum Replace | Aktif |

## 6. Format ZIP & Manifest

Struktur paket backup:

```
backup_<nama>_20261027_101500.zip
├── manifest.json
├── websites/
│   └── <website_uid>/            (satu folder per website)
│       ├── website.json
│       ├── pages.json
│       ├── views.json
│       ├── menus.json
│       ├── rewrites.json
│       ├── assets.json
│       ├── blog.json             (jika website_blog terpasang)
│       ├── events.json           (jika website_event terpasang)
│       └── shop.json             (jika website_sale terpasang)
├── data/
│   └── attachments.json          (metadata media, dipakai bersama)
└── media/
    ├── <attachment_uid>.png
    └── ...
```

Setiap record memakai **UID stabil** (`xml_id` atau `key` bila ada, selain itu UUID baru), bukan ID database, agar referensi antar-record bisa dipetakan ulang saat restore.

Contoh `manifest.json`:

```json
{
  "module": "export_import_web",
  "module_version": "17.0.1.0.0",
  "odoo_version": "17.0",
  "websites": [
    {"uid": "main", "name": "Company Site", "domain": "https://example.com",
     "counts": {"pages": 12, "views": 31, "menus": 9, "blog_posts": 24, "events": 3, "products": 58}}
  ],
  "installed_modules": ["website", "website_blog", "website_event", "website_sale"],
  "counts": {"attachments": 184},
  "total_size": 20971520,
  "created_at": "2026-10-27T10:15:00Z",
  "checksums": {"websites/main/pages.json": "sha256..."}
}
```

## 7. Algoritma Restore & Remap ID

Restore berjalan dalam satu transaksi database; error di langkah mana pun membatalkan semuanya.

1. **Validasi paket:** checksum, versi Odoo sama persis, dan semua modul di `installed_modules` yang dipakai kelompok terpilih terpasang di tujuan.
2. **Pratinjau & pemetaan:** pengguna memetakan tiap website dalam paket ke website tujuan (Replace) atau membuat baru (Create New), lalu memilih kelompok data.
3. **Snapshot:** backup otomatis website tujuan (jika Replace dan opsi aktif).
4. **Website:** update website tujuan atau buat website baru.
5. **Media lebih dulu:** upload `ir.attachment` baru, simpan peta `uid → id baru`.
6. **Data master eCommerce:** cocokkan atau buat kategori publik, atribut, dan nilai atribut; cocokkan UoM, kategori internal, dan pajak berdasar nama.
7. **View:** buat/update `ir.ui.view` berdasar `key`; view induk tertulis sebelum view turunan, lalu `inherit_id` diisi dari peta ID.
8. **Halaman, menu, redirect, asset:** buat/update dengan `view_id`, `parent_id`, dan `website_id` yang sudah di-remap.
9. **Konten modul:** blog lalu artikel, event lalu tiket, produk lalu varian dan gambar (hanya untuk modul terpasang dan kelompok terpilih).
10. **Penulisan ulang referensi:** di `arch_db`, konten artikel, deskripsi event, dan deskripsi produk, ganti `/web/image/<id lama>` dan `/web/content/<id lama>` dengan ID baru dari peta.
11. **Bersihkan:** hapus halaman, menu, redirect, dan asset website yang tidak ada di paket (hanya mode Replace, dengan konfirmasi, default tidak dicentang). Blog, artikel, event, dan produk **tidak pernah dihapus**; mode Replace untuk konten modul hanya membuat atau mengupdate. Terakhir, invalidasi cache asset dan website.
12. **Laporan:** tampilkan hasil dan catat di chatter.

Aturan khusus:

- View bawaan modul tidak ditimpa; hanya view kustom (`customize_show`, hasil editor, atau tanpa `xml_id` modul) yang direstore.
- Bila `key` bentrok dengan view milik modul lain, record dilewati dan dicatat sebagai peringatan.
- Domain website tidak diubah kecuali pengguna mencentang opsinya.
- Produk yang sudah ada di tujuan (cocok `default_code`) diupdate secara default; stok, pricelist pelanggan, dan akun akuntansi tidak disentuh.
- Hanya produk terpublikasi yang masuk backup: yang terikat ke website terpilih, atau tanpa website (`website_id` kosong, tampil di semua website).

## 8. Desain Data & UI/UX

### 8.1 Model

| Model | Field utama |
| --- | --- |
| `export.import.web.backup` | `name`, `website_ids` (Many2many), `backup_file` (Binary, attachment), `file_size`, `checksum`, `scope` (kelompok data), `backup_type` (manual / auto\_snapshot), `state`, `company_id`, pembuat dan tanggal |
| `export.import.web.restore.wizard` (transient) | `zip_file`, `manifest_info` (hasil parse), `line_ids`, `scope`, `create_snapshot`, `keep_domain`, `state` (upload / preview / done), `result_log` |
| `export.import.web.restore.line` (transient) | `source_website_uid`, `source_name`, `mode` (replace / create\_new), `target_website_id`, `new_website_name` |
| `res.config.settings` (tambahan) | Batas ukuran, retensi, snapshot default |

### 8.2 UI

Prinsip: bersih, lega, konsisten dengan gaya Odoo 17, aksi utama selalu terlihat.

- **List Backups:** kolom Nama, Website, Tipe (badge), Ukuran, Dibuat oleh, Tanggal. Tombol header: **Backup Now** dan **Restore**.
- **Form Backup:** tombol **Download** dan **Restore from this backup**, statusbar `Draft → Done`, smart button jumlah halaman/media, tab Info (checksum, daftar isi), chatter.
- **Wizard Backup:** pilih website, centang kelompok data, tombol **Create Backup** (primary).
- **Wizard Restore (3 langkah):** (1) upload ZIP dengan drag and drop, (2) pratinjau dan validasi (✔ / ✖, peringatan), (3) pilih mode, kelompok data, centang snapshot, lalu **Restore**. Setelah selesai tampil laporan hasil.
- Badge: hijau (Done), abu-abu (Draft), merah (Error), kuning (Auto snapshot).
- Ikon FontAwesome: `fa-download`, `fa-upload`, `fa-undo`, `fa-archive`.
- Pesan kosong ramah: "Buat backup pertama website Anda".
- Label bahasa Inggris dengan terjemahan Indonesia di `i18n/id.po`.

## 9. Keamanan & Hak Akses

Restore menulis view QWeb dan SCSS/JS ke sistem, sama dengan memasukkan kode. Fitur ini hanya untuk admin tepercaya.

| Risiko | Mitigasi |
| --- | --- |
| Paket berisi QWeb/JS berbahaya | Restore hanya untuk grup Manager/Administrator; peringatan jelas di wizard; hanya terima paket dengan checksum valid |
| Zip Slip (`../` di nama file) | Tolak path absolut dan `..`; nama media dipetakan ke UID, bukan nama asli |
| Zip bomb | Batas ukuran ekstrak, jumlah file, dan rasio kompresi |
| File media berbahaya | Whitelist tipe MIME/ekstensi gambar, font, video, PDF, dokumen; tolak executable |
| JSON rusak atau dimanipulasi | Validasi skema; parse dengan batas ukuran; abaikan field tak dikenal |
| Menimpa view bawaan modul | Hanya view kustom yang direstore; `key` milik modul dilewati |
| Kebocoran backup | Unduhan hanya lewat route terautentikasi dengan cek grup; attachment backup bersifat privat |
| Data lintas company | Record rule multi-company pada model backup; website tujuan harus milik company aktif |

| Grup | Hak |
| --- | --- |
| Export Import Web / User | Lihat riwayat backup dan unduh |
| Export Import Web / Manager | Buat backup, restore, hapus, konfigurasi |
| Administrator (`base.group_system`) | Semua hak |

## 10. Non-Fungsional & Struktur Modul

- **Performa:** backup website 500 media (total 100 MB) selesai di bawah 60 detik; backup katalog 1.000 produk (3 gambar per produk) selesai di bawah 5 menit; proses besar berjalan sebagai job di background dengan indikator progres.
- **Reliabilitas:** restore atomik dan snapshot otomatis; tidak ada perubahan parsial bila gagal.
- **Kompatibilitas:** Odoo 17.0, Python 3.10+, PostgreSQL 12+; Community dan Enterprise.
- **Multi-worker & hosting:** semua file lewat `ir.attachment`, tanpa ketergantungan filesystem lokal (aman untuk Odoo.sh).
- **Observability:** log `_logger` dan chatter untuk setiap backup dan restore.
- **Kualitas kode:** pylint-odoo bersih, unit test untuk backup, restore, remap ID, dan validasi keamanan.

```
export_import_web/
├── __init__.py
├── __manifest__.py
├── controllers/
│   └── main.py                  # download backup
├── models/
│   ├── backup.py                # export.import.web.backup
│   ├── exporter.py              # serialisasi website → JSON + media
│   ├── importer.py              # validasi, remap ID, penulisan ulang
│   └── res_config_settings.py
├── wizard/
│   ├── backup_wizard.py
│   └── restore_wizard.py
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
├── views/
│   ├── backup_views.xml
│   ├── wizard_views.xml
│   ├── res_config_settings_views.xml
│   └── menus.xml
├── static/description/          # icon.png, banner, index.html
├── i18n/id.po
├── tests/
└── LICENSE                      # teks OPL-1
```

## 11. Kriteria Penerimaan (UAT)

| # | Skenario | Hasil yang diharapkan |
| --- | --- | --- |
| 1 | Backup website dengan 10 halaman, menu, dan 50 gambar | ZIP terunduh dengan manifest, JSON, dan folder media; tercatat di riwayat |
| 2 | Restore ZIP ke instance Odoo baru (mode Create New) | Halaman, menu, dan gambar tampil identik; semua gambar termuat |
| 3 | Restore mode Replace di website yang sama | Konten tertimpa; snapshot website lama tersimpan di riwayat |
| 4 | Halaman berisi `/web/image/<id>` | URL gambar otomatis menunjuk ke ID attachment baru |
| 5 | View turunan (`inherit_id`) | Hubungan induk-turunan terbentuk benar setelah restore |
| 6 | ZIP dari Odoo versi mayor berbeda | Ditolak dengan pesan jelas |
| 7 | Modul yang dibutuhkan (mis. `website_blog`) belum terpasang | Peringatan di pratinjau; restore kelompok terkait diblokir, pengguna bisa lanjut dengan membatalkan centang kelompok tersebut |
| 8 | ZIP berisi `../evil` atau checksum tidak cocok | Ditolak; tidak ada perubahan data |
| 9 | Restore gagal di tengah proses | Rollback penuh; website lama utuh |
| 10 | User tanpa grup Manager | Menu tidak terlihat dan akses ditolak |

## 12. Listing, Lisensi & Roadmap

**Judul Apps Store:** Export & Import Web – Backup & Restore Your Odoo Website via ZIP

**Deskripsi singkat (listing):** Easily back up and restore your Odoo website with a single ZIP file. Export pages, menus, custom views, media, and optionally blog, event, and eCommerce catalog content, then restore them on the same database or on another Odoo instance with automatic ID mapping, validation, and safety snapshots.

**Fitur utama:** backup website lengkap dalam satu ZIP (termasuk blog, event, katalog eCommerce) · restore Replace atau Create New · pratinjau dan validasi sebelum restore · remap ID dan URL media otomatis · snapshot otomatis · UI bersih di menu Technical · multi-website dan multi-company.

**Harga:** USD 27,56 · **Lisensi:** OPL-1 (satu lisensi per instance produksi; distribusi ulang dilarang tanpa izin tertulis PT Niits Inovasi Teknologi).

Header pada setiap file Python/XML:

```python
# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan
```

| Fase | Cakupan | Estimasi |
| --- | --- | --- |
| 1. Fondasi | Model, menu, security, exporter halaman/view/menu, manifest | 1,5 minggu |
| 2. Media & Restore | Export media, importer, remap ID, penulisan ulang URL, snapshot | 2 minggu |
| 3. Konten modul | Exporter/importer blog, event, katalog eCommerce (varian, atribut, kategori, pencocokan UoM dan pajak) | 2,5 minggu |
| 4. UI & Wizard | Wizard backup/restore multi-website, pratinjau, laporan hasil | 1 minggu |
| 5. Hardening | Validasi keamanan, atomisitas, unit test (termasuk konten modul) | 1,5 minggu |
| 6. Rilis | i18n, dokumentasi, ikon dan banner, submit Apps Store | 0,5 minggu |
| **Total v1.0** | | **sekitar 9 minggu** |
| Pasca-rilis | Backup terjadwal (cron), backup ke storage eksternal (SFTP, S3) | Backlog |

## 13. Risiko & Keputusan

| Risiko | Dampak | Penanganan |
| --- | --- | --- |
| Struktur view dan snippet berubah antar patch Odoo 17 | Tampilan halaman bergeser setelah restore | Simpan versi Odoo di manifest; peringatkan bila berbeda; uji di beberapa patch |
| Halaman memakai snippet modul yang belum terpasang | Halaman rusak atau kosong | Cek `installed_modules` di pratinjau; pilihan lewati halaman terkait |
| Referensi ID tersembunyi di JS/SCSS atau field lain | Gambar atau link putus | Daftar pola URL yang ditulis ulang; laporan peringatan untuk pola yang tak dikenali |
| Website sangat besar | Timeout atau memori | Proses background, streaming per file, batas ukuran |
| Perbedaan domain antar instance | Link absolut salah | Opsi **keep domain** dan penulisan ulang domain lama ke baru |

**Keputusan (menggantikan pertanyaan terbuka):**

| # | Topik | Keputusan |
| --- | --- | --- |
| 1 | Cakupan v1.0 | Termasuk blog, event, dan katalog eCommerce |
| 2 | Versi Odoo | Restore hanya antar Odoo 17.0 |
| 3 | Backup terjadwal | Tidak di v1.0 (backlog) |
| 4 | Multi-website | Satu ZIP boleh berisi beberapa website |
| 5 | Storage eksternal | Tidak ada; unduh manual `.zip` |
| 6 | Replace dan penghapusan | Konten modul (blog, event, produk) tidak pernah dihapus; hanya halaman, menu, redirect, asset, dengan konfirmasi |
| 7 | Cakupan produk | Terpublikasi: terikat website terpilih atau tanpa website |
| 8 | Modul belum terpasang | Restore kelompok terkait diblokir sampai dicentang off |
| 9 | Batas ukuran | Default 200 MB / 1 GB, dapat diubah di Configuration |
| 10 | Tidak ikut backup | Komentar blog, pendaftar event, stok, pricelist pelanggan |
| 11 | Retensi snapshot | Terpisah dari backup manual, default 3 per website |
