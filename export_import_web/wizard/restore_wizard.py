# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan

import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ExportImportWebRestoreWizard(models.TransientModel):
    _name = 'export.import.web.restore.wizard'
    _description = 'Restore Website from ZIP'

    # ---- state machine: upload → preview → done ----
    state = fields.Selection(
        selection=[
            ('upload', 'Upload'),
            ('preview', 'Preview & Configure'),
            ('done', 'Done'),
        ],
        default='upload',
        required=True,
    )

    # ---- step 1: upload ----
    zip_file = fields.Binary(string='ZIP File', attachment=False)
    zip_filename = fields.Char(string='File Name')
    source_backup_id = fields.Many2one(
        'export.import.web.backup',
        string='Source Backup Record',
    )

    # ---- step 2: preview ----
    manifest_summary = fields.Text(string='Package Summary', readonly=True)
    validation_errors = fields.Text(string='Errors', readonly=True)
    validation_warnings = fields.Text(string='Warnings', readonly=True)
    has_errors = fields.Boolean(compute='_compute_has_errors')
    has_warnings = fields.Boolean(compute='_compute_has_warnings')
    warnings_acknowledged = fields.Boolean(string='I have read the warnings and wish to continue')

    line_ids = fields.One2many(
        'export.import.web.restore.line',
        'wizard_id',
        string='Website Mapping',
    )

    # scope
    include_pages = fields.Boolean(string='Pages, Views, Menus & Assets', default=True)
    include_media = fields.Boolean(string='Media', default=True)
    include_blog = fields.Boolean(string='Blog Content', default=True)
    include_events = fields.Boolean(string='Events', default=True)
    include_shop = fields.Boolean(string='eCommerce Catalog', default=True)

    blog_available = fields.Boolean(compute='_compute_module_availability')
    events_available = fields.Boolean(compute='_compute_module_availability')
    shop_available = fields.Boolean(compute='_compute_module_availability')

    create_snapshot = fields.Boolean(
        string='Create safety snapshot before Replace',
        default=True,
    )
    keep_domain = fields.Boolean(
        string='Keep existing domain (do not overwrite)',
        default=True,
    )

    # ---- step 3: done ----
    result_log = fields.Text(string='Restore Result', readonly=True)

    # ------------------------------------------------------------------ #
    # Computed                                                             #
    # ------------------------------------------------------------------ #
    @api.depends('validation_errors')
    def _compute_has_errors(self):
        for rec in self:
            rec.has_errors = bool(rec.validation_errors and rec.validation_errors.strip())

    @api.depends('validation_warnings')
    def _compute_has_warnings(self):
        for rec in self:
            rec.has_warnings = bool(
                rec.validation_warnings and rec.validation_warnings.strip()
            )

    @api.depends()
    def _compute_module_availability(self):
        def installed(name):
            return bool(self.env['ir.module.module'].sudo().search(
                [('name', '=', name), ('state', '=', 'installed')], limit=1
            ))
        for rec in self:
            rec.blog_available = installed('website_blog')
            rec.events_available = installed('website_event')
            rec.shop_available = installed('website_sale')

    # ------------------------------------------------------------------ #
    # Step 1 → 2: validate                                                 #
    # ------------------------------------------------------------------ #
    def action_validate(self):
        self.ensure_one()
        if not self.zip_file:
            raise UserError(_('Please upload a ZIP file first.'))
        self._action_do_validate()
        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new'}

    def _action_do_validate(self):
        """Parse ZIP, validate, build preview. Called internally too."""
        zip_bytes = base64.b64decode(self.zip_file)
        importer = self.env['export.import.web.importer']
        manifest, errors, warnings = importer.validate(zip_bytes)

        # Build summary text
        if manifest.get('websites'):
            lines = [
                f"📦  Odoo {manifest.get('odoo_version', '?')}  |  "
                f"Created: {manifest.get('created_at', '?')}",
                "",
            ]
            for ws in manifest['websites']:
                c = ws.get('counts', {})
                lines.append(f"🌐  {ws['name']}  ({ws.get('domain', '')})")
                lines.append(
                    f"    Pages: {c.get('pages', 0)}  |  Views: {c.get('views', 0)}  |  "
                    f"Menus: {c.get('menus', 0)}  |  Media: {manifest.get('counts', {}).get('attachments', 0)}"
                )
                if c.get('blog_posts'):
                    lines.append(f"    Blog posts: {c['blog_posts']}")
                if c.get('events'):
                    lines.append(f"    Events: {c['events']}")
                if c.get('products'):
                    lines.append(f"    Products: {c['products']}")
        else:
            lines = ['No website data found in package.']

        self.manifest_summary = '\n'.join(lines)
        self.validation_errors = '\n'.join(errors) if errors else ''
        self.validation_warnings = '\n'.join(warnings) if warnings else ''

        # Build website mapping lines
        self.line_ids.unlink()
        for ws in manifest.get('websites', []):
            self.env['export.import.web.restore.line'].create({
                'wizard_id': self.id,
                'source_website_uid': ws['uid'],
                'source_name': ws['name'],
                'mode': 'create_new',
                'new_website_name': ws['name'] + ' (restored)',
            })

        self.state = 'preview'

    # ------------------------------------------------------------------ #
    # Step 2 → 3: restore                                                  #
    # ------------------------------------------------------------------ #
    def action_restore(self):
        self.ensure_one()
        if self.has_errors:
            raise UserError(_('Please resolve all validation errors before restoring.'))
        if self.has_warnings and not self.warnings_acknowledged:
            raise UserError(_(
                'Please acknowledge the warnings by checking '
                '"I have read the warnings and wish to continue".'
            ))

        zip_bytes = base64.b64decode(self.zip_file)
        scope = {
            'include_pages': self.include_pages,
            'include_media': self.include_media,
            'include_blog': self.include_blog and self.blog_available,
            'include_events': self.include_events and self.events_available,
            'include_shop': self.include_shop and self.shop_available,
        }

        lines_data = []
        for line in self.line_ids:
            lines_data.append({
                'source_website_uid': line.source_website_uid,
                'mode': line.mode,
                'target_website_id': line.target_website_id.id if line.target_website_id else False,
                'new_website_name': line.new_website_name,
            })

        importer = self.env['export.import.web.importer']
        try:
            result = importer.restore(
                zip_bytes, lines_data, scope, self.create_snapshot
            )
        except Exception as exc:
            raise UserError(_('Restore failed: %s') % str(exc)) from exc

        # Format result log
        log_lines = [
            f"✅ Restore completed",
            f"   Created:  {result['created']}",
            f"   Updated:  {result['updated']}",
            f"   Skipped:  {result['skipped']}",
        ]
        if result.get('warnings'):
            log_lines.append("")
            log_lines.append("⚠ Warnings:")
            for w in result['warnings']:
                log_lines.append(f"   • {w}")

        self.write({
            'result_log': '\n'.join(log_lines),
            'state': 'done',
        })
        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new'}

    def action_back(self):
        self.state = 'upload'
        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new'}


class ExportImportWebRestoreLine(models.TransientModel):
    _name = 'export.import.web.restore.line'
    _description = 'Website Restore Mapping Line'

    wizard_id = fields.Many2one(
        'export.import.web.restore.wizard',
        required=True,
        ondelete='cascade',
    )
    source_website_uid = fields.Char(string='Source UID', readonly=True)
    source_name = fields.Char(string='Source Website', readonly=True)
    mode = fields.Selection(
        selection=[
            ('replace', 'Replace Existing'),
            ('create_new', 'Create New Website'),
        ],
        string='Mode',
        default='create_new',
        required=True,
    )
    target_website_id = fields.Many2one(
        'website',
        string='Target Website',
    )
    new_website_name = fields.Char(string='New Website Name')
