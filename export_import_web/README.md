# Export & Import Web for Odoo 18

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-875A7B.svg?style=flat-square)](https://www.odoo.com)
[![License](https://img.shields.io/badge/License-OPL--1-blue.svg?style=flat-square)](https://www.odoo.com/documentation/18.0/legal/licenses.html)
[![Price](https://img.shields.io/badge/Price-USD%2014.20-green.svg?style=flat-square)](https://apps.odoo.com)
[![CE+EE](https://img.shields.io/badge/Edition-CE%20%26%20EE-purple.svg?style=flat-square)](https://www.odoo.com)

**Backup and restore your entire Odoo website with a single ZIP file.**

Export pages, menus, custom views, media attachments, and optionally blog posts, events,
and eCommerce catalog content. Restore to the same database or another Odoo 18 instance
with automatic ID remapping, URL rewriting, safety snapshots, and full rollback on failure.

---

## ✨ Key Features

- **One-click backup** of one or multiple websites into a single portable ZIP
- **Smart restore** with 3-step wizard: upload → preview → restore
- **Automatic ID remapping** — `/web/image/<id>` URLs are rewritten to new IDs
- **Safety snapshot** auto-created before every Replace restore
- **Supports `website_blog`, `website_event`, `website_sale`** (auto-detected at runtime)
- **Multi-website** — one ZIP can contain several websites
- **Multi-company** support with record-level access control
- **Atomic restore** — full rollback on failure, no partial writes
- **Security hardening** — Zip Slip guard, zip bomb protection, MIME whitelist, checksum verification
- **Background job** via cron one-shot — no UI blocking for large backups

---

## 📋 Compatibility

| Feature | Details |
|---|---|
| Odoo version | 18.0 |
| Editions | Community & Enterprise |
| Hosting | Self-hosted, Odoo.sh |
| Python | 3.10+ |
| PostgreSQL | 12+ |
| Extra packages | None required |

> ⚠ Restore only between instances running the **same Odoo version** (18.0).

---

## 🚀 Installation

1. Copy or clone the `export_import_web` folder to your Odoo `addons/` directory.
2. Restart Odoo.
3. Enable Developer Mode (**Settings → General Settings → Developer Tools → Activate**).
4. Go to **Apps**, click **Update Apps List**, search for `Export Import Web`, and install.

---

## 🛠 Usage

### Creating a Backup

1. Navigate to **Website → Export & Import Web → Backups**
2. Click **Backup Now**
3. Select the website(s) to include
4. Choose content groups (Pages, Media, Blog, Events, Shop)
5. Click **Create Backup** — the job runs in the background
6. Refresh the page; when status is **Done**, click **Download ZIP**

### Restoring from a Backup

1. Navigate to **Website → Export & Import Web → Restore**
   (or open a backup record and click **Restore from this Backup**)
2. Upload the `.zip` file
3. Click **Validate ZIP** — review the preview and any warnings
4. Map each source website to a target (Replace or Create New)
5. Configure options (snapshot, domain, scope)
6. Click **Restore**

---

## ⚙ Configuration

Go to **Website → Export & Import Web → Configuration** (or **Settings → Website**):

| Setting | Default | Description |
|---|---|---|
| ZIP Upload Limit (MB) | 200 | Max size of uploaded ZIP |
| Max Uncompressed Size (MB) | 1024 | Zip bomb protection |
| Manual Backup Retention | 5 | Max manual backups per website (0 = unlimited) |
| Snapshot Retention | 3 | Max auto-snapshots per website |
| Snapshot before Replace | On | Auto-create safety copy before overwriting |

---

## 🔒 Access Control

| Group | Rights |
|---|---|
| Export Import Web / User | View and download backups |
| Export Import Web / Manager | Create, restore, delete, configure |

---

## ⚠ Limitations (v1.0)

- Restore only between Odoo **18.0** instances (same version required)
- No scheduled backups — manual only
- No external storage (S3, SFTP) — ZIP downloaded to browser
- Transactional data not included: orders, event registrations, blog comments, stock
- Blog/Events/Shop restore requires the respective module on the target instance

---

## 🤝 Support

- **Duration:** 90 days from purchase date
- **Email:** [sqlrif@gmail.com](mailto:sqlrif@gmail.com)
- **Website:** [www.niits.id](https://www.niits.id)
- WhatsApp provided after purchase only

---

## 📄 License

OPL-1 — Copyright © 2024 PT Niits Inovasi Teknologi. Author: Arif N Ramadhan.  
This module may only be used if you have purchased a valid license from the Odoo Apps Store.
