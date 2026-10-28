# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/) and Semantic Versioning (`17.0.MAJOR.MINOR.PATCH`).

## [17.0.1.0.0] - Initial Release (Planned)

### Added
- Menu **Export & Import Web** under Website with submenus: Backups, Restore, Configuration.
- Model `export.import.web.backup` for storing backup records with state tracking and chatter.
- **Backup wizard** (`export.import.web.backup.wizard`) with website and scope selection.
- **Restore wizard** (`export.import.web.restore.wizard`) with 3-step flow: upload → preview → restore.
- Exporter engine (`WebsiteExporter`) — serialises pages, views, menus, rewrites, assets, media, blog, events, eCommerce to ZIP.
- Importer engine (`WebsiteImporter`) — validates ZIP, remaps IDs, rewrites `/web/image` URLs, restores all content atomically.
- Background job via cron one-shot for non-blocking backup of large websites.
- Automatic safety snapshot before every Replace restore.
- Retention policy: configurable max backups per website (manual and snapshot separately).
- Security: Zip Slip guard, zip bomb protection, MIME whitelist, SHA-256 checksum verification.
- Multi-website: one ZIP can contain multiple websites; per-website mapping at restore time.
- Multi-company record rules.
- Settings section in Website → Configuration → Settings.
- HTTP download controller at `/export_import_web/download/<id>` (authenticated).
- Indonesian translation (`i18n/id.po`), POT template.
- `README.md`, `CHANGELOG.md`, `LICENSE` (OPL-1).
- `static/description/index.html`, `icon.png`, `banner.png` for Odoo Apps Store.

## [17.0.1.1.0] - Planned

### Added
- Scheduled backup via cron (optional).
- Progress bar for large backup jobs.
- Export/import configuration (Settings values) as part of ZIP.

## [17.0.1.2.0] - Planned

### Added
- External storage support (SFTP, S3) for backup files.
- Diff preview before restore (show changed records).
