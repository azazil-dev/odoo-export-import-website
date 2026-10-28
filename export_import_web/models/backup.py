# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan

import base64
import hashlib
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ExportImportWebBackup(models.Model):
    _name = 'export.import.web.backup'
    _description = 'Website Backup'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ------------------------------------------------------------------ #
    # Core fields                                                          #
    # ------------------------------------------------------------------ #
    name = fields.Char(
        string='Backup Name',
        required=True,
        tracking=True,
    )
    website_ids = fields.Many2many(
        'website',
        'eiw_backup_website_rel',
        'backup_id',
        'website_id',
        string='Websites',
        tracking=True,
    )
    backup_file = fields.Binary(
        string='ZIP File',
        attachment=True,
        groups='export_import_web.group_export_import_web_user',
        copy=False,
    )
    backup_filename = fields.Char(string='File Name', copy=False)
    file_size = fields.Integer(string='File Size (bytes)', readonly=True, copy=False)
    file_size_kb = fields.Float(
        string='Size (KB)',
        compute='_compute_file_size_kb',
        store=False,
    )
    checksum = fields.Char(
        string='SHA-256 Checksum',
        readonly=True,
        copy=False,
    )
    scope = fields.Char(
        string='Scope (JSON)',
        default='{}',
        help='JSON dict of included content groups',
    )
    backup_type = fields.Selection(
        selection=[
            ('manual', 'Manual'),
            ('auto_snapshot', 'Auto Snapshot'),
        ],
        string='Type',
        default='manual',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('running', 'Running'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    result_log = fields.Text(string='Result Log', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    # ------------------------------------------------------------------ #
    # Computed                                                             #
    # ------------------------------------------------------------------ #
    @api.depends('file_size')
    def _compute_file_size_kb(self):
        for rec in self:
            rec.file_size_kb = round(rec.file_size / 1024, 1) if rec.file_size else 0.0

    # ------------------------------------------------------------------ #
    # Name generation                                                      #
    # ------------------------------------------------------------------ #
    def _compute_filename(self):
        """Return a descriptive ZIP filename."""
        ts = fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(self.website_ids) == 1:
            slug = self.website_ids.name.lower().replace(' ', '_')[:30]
            return f'backup_{slug}_{ts}.zip'
        return f'backup_multi_{ts}.zip'

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #
    def action_download(self):
        """Return URL action to download the backup ZIP."""
        self.ensure_one()
        if self.state != 'done' or not self.backup_file:
            raise UserError(_('Backup is not ready for download yet.'))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export_import_web/download/{self.id}',
            'target': 'self',
        }

    def action_restore_from_backup(self):
        """Open the restore wizard pre-loaded with this backup's file."""
        self.ensure_one()
        if self.state != 'done' or not self.backup_file:
            raise UserError(_('This backup has no file to restore from.'))
        wizard = self.env['export.import.web.restore.wizard'].create({
            'zip_file': self.backup_file,
            'zip_filename': self.backup_filename or (self.name + '.zip'),
            'source_backup_id': self.id,
        })
        wizard._action_do_validate()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Restore Website'),
            'res_model': 'export.import.web.restore.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_refresh_status(self):
        """Reload the current form (polling helper while state=running)."""
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    # ------------------------------------------------------------------ #
    # Background job (cron one-shot)                                       #
    # ------------------------------------------------------------------ #
    def action_run_in_background(self):
        """Schedule backup as a cron one-shot job and return immediately."""
        self.ensure_one()
        self.write({'state': 'running'})
        cron = self.env['ir.cron'].sudo().create({
            'name': f'EIW Backup #{self.id}: {self.name}',
            'model_id': self.env['ir.model'].sudo().search(
                [('model', '=', self._name)], limit=1
            ).id,
            'state': 'code',
            'code': f"model.browse({self.id})._run_backup_job()",
            'nextcall': fields.Datetime.now(),
            'active': True,
            'priority': 5,
        })
        cron._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Backup Started'),
                'message': _(
                    'Backup "%s" is running in the background. '
                    'Refresh the page in a few seconds to check the result.'
                ) % self.name,
                'type': 'info',
                'sticky': False,
            },
        }

    def _run_backup_job(self):
        """Called by the cron one-shot to perform the actual export."""
        try:
            scope = json.loads(self.scope or '{}')
            exporter = self.env['export.import.web.exporter']
            zip_bytes, manifest = exporter.export(self.website_ids.ids, scope)

            checksum = hashlib.sha256(zip_bytes).hexdigest()
            filename = self._compute_filename()

            self.write({
                'state': 'done',
                'backup_file': base64.b64encode(zip_bytes).decode(),
                'backup_filename': filename,
                'file_size': len(zip_bytes),
                'checksum': checksum,
                'result_log': json.dumps(manifest.get('counts', {}), indent=2),
            })

            # Apply retention policy
            for website in self.website_ids:
                self._apply_retention(website.id)
                self._apply_snapshot_retention(website.id)

            self.message_post(
                body=_('✅ Backup completed successfully. Size: %s KB, SHA-256: %s…')
                % (len(zip_bytes) // 1024, checksum[:16])
            )
            _logger.info('EIW backup #%s completed (%s KB)', self.id, len(zip_bytes) // 1024)

        except Exception as exc:
            self.write({'state': 'error', 'result_log': str(exc)})
            self.message_post(body=_('❌ Backup failed: %s') % str(exc))
            _logger.exception('EIW backup #%s failed', self.id)
        finally:
            cron = self.env['ir.cron'].sudo().search([
                ('model_name', '=', self._name),
                ('code', '=', f"model.browse({self.id})._run_backup_job()"),
            ])
            if cron:
                cron.unlink()

    # ------------------------------------------------------------------ #
    # Retention                                                            #
    # ------------------------------------------------------------------ #
    def _apply_retention(self, website_id):
        limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'export_import_web.retention_manual', '5'
        ))
        if limit == 0:
            return
        backups = self.search([
            ('backup_type', '=', 'manual'),
            ('website_ids', 'in', [website_id]),
            ('state', '=', 'done'),
        ], order='create_date desc')
        to_delete = backups[limit:]
        if to_delete:
            to_delete.unlink()

    def _apply_snapshot_retention(self, website_id):
        limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'export_import_web.retention_snapshot', '3'
        ))
        if limit == 0:
            return
        snapshots = self.search([
            ('backup_type', '=', 'auto_snapshot'),
            ('website_ids', 'in', [website_id]),
            ('state', '=', 'done'),
        ], order='create_date desc')
        to_delete = snapshots[limit:]
        if to_delete:
            to_delete.unlink()
