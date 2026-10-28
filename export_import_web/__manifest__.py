# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan
{
    'name': 'Export & Import Web',
    'version': '18.0.1.0.0',
    'summary': 'Backup & restore your Odoo website (pages, menus, media, blog, events, shop) via ZIP',
    'description': """
Export & Import Web
===================
Backup and restore your entire Odoo website with a single ZIP file.

Export pages, menus, custom views, media attachments, and optionally
blog posts, events, and eCommerce catalog content.

Restore to the same database or another Odoo 18 instance with automatic
ID remapping, URL rewriting, safety snapshots, and full rollback on failure.

Features
--------
- One-click backup of one or multiple websites into a single ZIP
- Selective restore: Replace existing website or Create New
- Automatic ID remapping and /web/image URL rewriting
- Safety snapshot before every Replace operation
- Supports website_blog, website_event, website_sale (auto-detected)
- Multi-website and multi-company support
- Atomic restore with full rollback on failure
- Background job for large websites (non-blocking UI)

Limitations
-----------
- Restore only between instances running the same Odoo version (18.0)
- No scheduled backups (manual only)
- No external storage (SFTP, S3) — ZIP is downloaded to your browser
    """,
    'category': 'Website',
    'author': 'Arif N Ramadhan',
    'maintainer': 'PT Niits Inovasi Teknologi',
    'website': 'https://www.niits.id',
    'support': 'sqlrif@gmail.com',
    'license': 'OPL-1',
    'price': 27.50,
    'currency': 'USD',
    'depends': ['base', 'web', 'mail', 'website'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/config_data.xml',
        'views/backup_views.xml',
        'views/wizard_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
