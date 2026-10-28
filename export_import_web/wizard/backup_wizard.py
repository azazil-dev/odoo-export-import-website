# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ExportImportWebBackupWizard(models.TransientModel):
    _name = 'export.import.web.backup.wizard'
    _description = 'Create Website Backup'

    website_ids = fields.Many2many(
        'website',
        string='Websites',
        required=True,
        help='Select one or more websites to include in this backup.',
    )

    # ---- scope toggles ----
    include_pages = fields.Boolean(
        string='Pages, Views, Menus & Assets',
        default=True,
    )
    include_media = fields.Boolean(
        string='Media (Images & Attachments)',
        default=True,
    )
    include_blog = fields.Boolean(
        string='Blog Content',
        default=True,
    )
    include_events = fields.Boolean(
        string='Events',
        default=True,
    )
    include_shop = fields.Boolean(
        string='eCommerce Catalog (Products)',
        default=True,
    )

    # ---- computed visibility ----
    blog_available = fields.Boolean(compute='_compute_module_availability')
    events_available = fields.Boolean(compute='_compute_module_availability')
    shop_available = fields.Boolean(compute='_compute_module_availability')

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
    def action_create_backup(self):
        """Create the backup record and schedule the cron one-shot job."""
        self.ensure_one()
        if not self.website_ids:
            raise UserError(_('Please select at least one website.'))

        scope = {
            'include_pages': self.include_pages,
            'include_media': self.include_media,
            'include_blog': self.include_blog and self.blog_available,
            'include_events': self.include_events and self.events_available,
            'include_shop': self.include_shop and self.shop_available,
        }

        # Build a readable name
        if len(self.website_ids) == 1:
            website_name = self.website_ids.name
        else:
            website_name = ', '.join(self.website_ids.mapped('name'))

        backup = self.env['export.import.web.backup'].create({
            'name': f'Backup – {website_name}',
            'website_ids': [(6, 0, self.website_ids.ids)],
            'scope': json.dumps(scope),
            'backup_type': 'manual',
            'state': 'draft',
            'company_id': self.env.company.id,
        })

        return backup.action_run_in_background()
