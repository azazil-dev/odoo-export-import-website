# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eiw_max_zip_size_mb = fields.Integer(
        string='Max ZIP upload size (MB)',
        default=200,
        config_parameter='export_import_web.max_zip_size_mb',
        help='Maximum size of a ZIP file that can be uploaded for restore.',
    )
    eiw_max_extract_size_mb = fields.Integer(
        string='Max uncompressed size (MB)',
        default=1024,
        config_parameter='export_import_web.max_extract_size_mb',
        help='Maximum total uncompressed size allowed during restore. '
             'Protects against zip bombs.',
    )
    eiw_retention_manual = fields.Integer(
        string='Manual backup retention per website',
        default=5,
        config_parameter='export_import_web.retention_manual',
        help='Maximum number of manual backups kept per website. '
             '0 = unlimited.',
    )
    eiw_retention_snapshot = fields.Integer(
        string='Auto-snapshot retention per website',
        default=3,
        config_parameter='export_import_web.retention_snapshot',
        help='Maximum number of auto-snapshots kept per website (separate from manual backups).',
    )
    eiw_create_snapshot = fields.Boolean(
        string='Create snapshot before Replace restore',
        default=True,
        config_parameter='export_import_web.create_snapshot',
        help='Automatically create a safety snapshot of the target website '
             'before overwriting it in Replace mode.',
    )
