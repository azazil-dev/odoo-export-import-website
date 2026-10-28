# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan

import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ExportImportWebController(http.Controller):

    @http.route(
        '/export_import_web/download/<int:backup_id>',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def download_backup(self, backup_id, **kwargs):
        """Authenticated download route for backup ZIP files."""
        # Auth: must be at least a User of the module
        if not request.env.user.has_group(
            'export_import_web.group_export_import_web_user'
        ):
            return request.not_found()

        backup = request.env['export.import.web.backup'].browse(backup_id)
        if not backup.exists() or backup.state != 'done':
            return request.not_found()

        # Multi-company guard
        if backup.company_id and backup.company_id not in request.env.user.company_ids:
            return request.not_found()

        if not backup.backup_file:
            return request.not_found()

        filename = backup.backup_filename or f'backup_{backup_id}.zip'
        if not filename.endswith('.zip'):
            filename += '.zip'

        # Try to serve via ir.attachment for streaming
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'export.import.web.backup'),
            ('res_field', '=', 'backup_file'),
            ('res_id', '=', backup_id),
        ], limit=1)

        if attachment and attachment.datas:
            raw = base64.b64decode(attachment.datas)
        else:
            # Fallback: read directly from field
            raw = base64.b64decode(backup.backup_file)

        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Content-Length', str(len(raw))),
        ]
        return request.make_response(raw, headers=headers)
