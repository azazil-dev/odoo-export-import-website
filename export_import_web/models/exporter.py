# -*- coding: utf-8 -*-
# Part of PT Niits Inovasi Teknologi. See LICENSE file for full copyright and licensing details.
# Author: Arif N Ramadhan

"""
WebsiteExporter — serialises one or more Odoo websites into a ZIP archive.

ZIP structure:
    manifest.json
    websites/<uid>/website.json
    websites/<uid>/pages.json
    websites/<uid>/views.json
    websites/<uid>/menus.json
    websites/<uid>/rewrites.json
    websites/<uid>/assets.json
    websites/<uid>/blog.json        (if website_blog installed + in scope)
    websites/<uid>/events.json      (if website_event installed + in scope)
    websites/<uid>/shop.json        (if website_sale installed + in scope)
    data/attachments.json
    media/<uid>.<ext>
"""

import base64
import hashlib
import io
import json
import logging
import mimetypes
import os
import re
import uuid
import zipfile

import odoo.release
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo import _

_logger = logging.getLogger(__name__)

# MIME types allowed in media folder
_ALLOWED_MIME_PREFIXES = (
    'image/', 'video/', 'audio/', 'font/',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument',
    'application/vnd.ms-',
    'application/font-',
    'application/x-font-',
)
_BLOCKED_EXTENSIONS = {
    '.exe', '.sh', '.py', '.php', '.js', '.html', '.htm',
    '.bat', '.cmd', '.ps1', '.vbs', '.rb', '.pl', '.jar',
}


class WebsiteExporter(models.AbstractModel):
    _name = 'export.import.web.exporter'
    _description = 'Website Exporter Engine'

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    @api.model
    def export(self, website_ids, scope):
        """
        Export the given website IDs according to *scope* dict.

        scope keys (all bool, default True if absent):
            include_pages, include_media, include_blog,
            include_events, include_shop

        Returns (zip_bytes: bytes, manifest: dict).
        """
        websites = self.env['website'].browse(website_ids)
        if not websites:
            raise UserError(_('No websites selected for backup.'))

        website_data = []
        all_attachment_uids = {}  # uid → attachment record (shared across websites)

        for website in websites:
            data = self._export_website(website, scope, all_attachment_uids)
            website_data.append(data)

        # Serialize attachments
        attachments_json, media_files = self._serialize_attachments(all_attachment_uids)

        manifest = self._build_manifest(website_data, scope, all_attachment_uids)
        zip_bytes = self._build_zip(website_data, attachments_json, media_files, manifest)
        return zip_bytes, manifest

    # ------------------------------------------------------------------ #
    # Per-website export                                                   #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_website(self, website, scope, attachment_uid_map):
        """Collect all data for one website. Returns a dict."""
        include_pages = scope.get('include_pages', True)
        include_media = scope.get('include_media', True)
        include_blog = scope.get('include_blog', True)
        include_events = scope.get('include_events', True)
        include_shop = scope.get('include_shop', True)

        uid = self._get_website_uid(website)
        data = {
            'uid': uid,
            'website': self._export_website_record(website),
        }

        # Collect arch strings to scan for referenced attachment IDs
        arch_strings = []

        if include_pages:
            data['pages'] = self._export_pages(website)
            data['views'] = self._export_views(website, arch_strings)
            data['menus'] = self._export_menus(website)
            data['rewrites'] = self._export_rewrites(website)
            data['assets'] = self._export_assets(website)
        else:
            data['pages'] = []
            data['views'] = []
            data['menus'] = []
            data['rewrites'] = []
            data['assets'] = []

        if include_blog and self._module_installed('website_blog'):
            data['blog'] = self._export_blog(website)
            for post in data['blog'].get('posts', []):
                arch_strings.append(post.get('content', ''))
        else:
            data['blog'] = None

        if include_events and self._module_installed('website_event'):
            data['events'] = self._export_events(website)
        else:
            data['events'] = None

        if include_shop and self._module_installed('website_sale'):
            data['shop'] = self._export_shop(website, attachment_uid_map)
        else:
            data['shop'] = None

        # Collect media referenced in arch
        if include_media:
            self._collect_media_from_arch(arch_strings, website, attachment_uid_map)

        return data

    # ------------------------------------------------------------------ #
    # UID helpers                                                          #
    # ------------------------------------------------------------------ #
    @api.model
    def _get_website_uid(self, website):
        imd = self.env['ir.model.data'].sudo().search(
            [('model', '=', 'website'), ('res_id', '=', website.id)], limit=1
        )
        if imd:
            return f"{imd.module}.{imd.name}"
        return f"website_{website.id}"

    @api.model
    def _get_record_uid(self, record, key_field=None):
        """Stable UID: xml_id if available, else uuid5 from model+id."""
        imd = self.env['ir.model.data'].sudo().search(
            [('model', '=', record._name), ('res_id', '=', record.id)], limit=1
        )
        if imd:
            return f"{imd.module}.{imd.name}"
        seed = key_field and getattr(record, key_field, None) or f"{record._name}/{record.id}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, str(seed)))

    # ------------------------------------------------------------------ #
    # Website record                                                       #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_website_record(self, website):
        return {
            'id': website.id,
            'name': website.name,
            'domain': website.domain or '',
            'default_lang_id': website.default_lang_id.code if website.default_lang_id else 'en_US',
            'company_id': website.company_id.id if website.company_id else False,
            'company_name': website.company_id.name if website.company_id else '',
        }

    # ------------------------------------------------------------------ #
    # Pages                                                                #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_pages(self, website):
        pages = self.env['website.page'].search([
            '|', ('website_id', '=', website.id), ('website_id', '=', False)
        ])
        result = []
        for page in pages:
            result.append({
                'uid': self._get_record_uid(page, 'url'),
                'url': page.url,
                'name': page.name,
                'is_published': page.is_published,
                'website_published': page.website_published,
                'view_key': page.view_id.key if page.view_id else False,
                'date_publish': str(page.date_publish) if page.date_publish else False,
                'seo_name': page.seo_name or '',
                'website_meta_description': page.website_meta_description or '',
            })
        return result

    # ------------------------------------------------------------------ #
    # Views (custom only)                                                  #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_views(self, website, arch_strings_out):
        """Export custom QWeb views for this website."""
        views = self.env['ir.ui.view'].search([
            ('website_id', '=', website.id),
            ('type', '=', 'qweb'),
        ])
        result = []
        for view in views:
            if not self._is_custom_view(view):
                continue
            if view.arch_db:
                arch_strings_out.append(view.arch_db)
            parent_uid = False
            if view.inherit_id:
                parent_uid = self._get_record_uid(view.inherit_id, 'key')
            result.append({
                'uid': self._get_record_uid(view, 'key'),
                'key': view.key or '',
                'arch_db': view.arch_db or '',
                'inherit_uid': parent_uid,
                'active': view.active,
                'priority': view.priority,
                'customize_show': view.customize_show,
                'name': view.name or '',
            })
        return result

    @api.model
    def _is_custom_view(self, view):
        """True if this view is user-customised (not owned by an installed module)."""
        if not view.key:
            return True  # no key → purely custom
        imd = self.env['ir.model.data'].sudo().search([
            ('model', '=', 'ir.ui.view'),
            ('res_id', '=', view.id),
        ], limit=1)
        if not imd:
            return True  # no xml_id → custom
        if imd.module in ('__export__', '__custom__', '__import__'):
            return True
        # If the owning module is still installed it's a core view — skip
        installed = self._module_installed(imd.module)
        return not installed

    # ------------------------------------------------------------------ #
    # Menus                                                                #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_menus(self, website):
        menus = self.env['website.menu'].search([
            ('website_id', '=', website.id)
        ], order='id')
        result = []
        for menu in menus:
            result.append({
                'uid': self._get_record_uid(menu),
                'name': menu.name,
                'url': menu.url or '',
                'page_uid': self._get_record_uid(menu.page_id, 'url') if menu.page_id else False,
                'parent_uid': self._get_record_uid(menu.parent_id) if menu.parent_id else False,
                'sequence': menu.sequence,
                'is_visible': menu.is_visible,
            })
        return result

    # ------------------------------------------------------------------ #
    # Rewrites                                                             #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_rewrites(self, website):
        if 'website.rewrite' not in self.env:
            return []
        rewrites = self.env['website.rewrite'].search([
            ('website_id', '=', website.id)
        ])
        return [
            {
                'uid': self._get_record_uid(rw),
                'url_from': rw.url_from,
                'url_to': rw.url_to or '',
                'redirect_type': rw.redirect_type,
                'active': rw.active,
            }
            for rw in rewrites
        ]

    # ------------------------------------------------------------------ #
    # Assets                                                               #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_assets(self, website):
        if 'ir.asset' not in self.env:
            return []
        assets = self.env['ir.asset'].search([
            ('website_id', '=', website.id)
        ])
        return [
            {
                'uid': self._get_record_uid(asset, 'name'),
                'name': asset.name,
                'bundle': asset.bundle,
                'path': asset.path,
                'directive': asset.directive,
                'active': asset.active,
                'sequence': asset.sequence,
            }
            for asset in assets
        ]

    # ------------------------------------------------------------------ #
    # Media / attachments                                                  #
    # ------------------------------------------------------------------ #
    @api.model
    def _collect_media_from_arch(self, arch_strings, website, uid_map):
        """Find /web/image/<id> and /web/content/<id> refs in arch strings."""
        pattern = re.compile(r'/web/(?:image|content)/(\d+)')
        ids_found = set()
        for arch in arch_strings:
            for m in pattern.finditer(arch or ''):
                ids_found.add(int(m.group(1)))

        if not ids_found:
            return

        attachments = self.env['ir.attachment'].sudo().browse(list(ids_found)).exists()
        for att in attachments:
            att_uid = self._get_record_uid(att)
            if att_uid not in uid_map:
                uid_map[att_uid] = att

    @api.model
    def _serialize_attachments(self, uid_map):
        """
        Returns:
            attachments_json: list of dicts for data/attachments.json
            media_files: dict {zip_path: bytes}
        """
        attachments_json = []
        media_files = {}

        for uid, att in uid_map.items():
            if not att.datas:
                continue
            mimetype = att.mimetype or 'application/octet-stream'
            filename = att.name or f'{uid}.bin'
            if not self._check_mime(mimetype, filename):
                _logger.warning('EIW: skipped attachment %s (blocked MIME %s)', filename, mimetype)
                continue

            ext = os.path.splitext(filename)[1].lower() or self._ext_from_mime(mimetype)
            zip_path = f'media/{uid}{ext}'

            attachments_json.append({
                'uid': uid,
                'original_id': att.id,
                'name': filename,
                'mimetype': mimetype,
                'url': att.url or '',
                'zip_path': zip_path,
                'checksum': att.checksum or '',
                'res_model': att.res_model or '',
                'res_id': att.res_id or 0,
            })
            try:
                media_files[zip_path] = base64.b64decode(att.datas)
            except Exception:
                _logger.warning('EIW: could not decode attachment %s', att.id)

        return attachments_json, media_files

    @staticmethod
    def _check_mime(mimetype, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext in _BLOCKED_EXTENSIONS:
            return False
        for prefix in _ALLOWED_MIME_PREFIXES:
            if mimetype.startswith(prefix):
                return True
        return False

    @staticmethod
    def _ext_from_mime(mimetype):
        ext = mimetypes.guess_extension(mimetype)
        return ext or '.bin'

    # ------------------------------------------------------------------ #
    # Blog (website_blog)                                                  #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_blog(self, website):
        blogs = self.env['blog.blog'].search([
            '|', ('website_id', '=', website.id), ('website_id', '=', False)
        ])
        tags = self.env['blog.tag'].search([])
        tag_categories = self.env['blog.tag.category'].search([]) if \
            'blog.tag.category' in self.env else self.env['blog.tag'].browse()

        blog_list = []
        for blog in blogs:
            posts = self.env['blog.post'].search([('blog_id', '=', blog.id)])
            post_list = []
            for post in posts:
                cover_uid = False
                if post.cover_properties:
                    # extract attachment id from cover_properties JSON
                    try:
                        cover = json.loads(post.cover_properties)
                        bg = cover.get('background-image', '')
                        m = re.search(r'/web/image/(\d+)', bg)
                        if m:
                            att = self.env['ir.attachment'].sudo().browse(int(m.group(1)))
                            if att.exists():
                                cover_uid = self._get_record_uid(att)
                    except Exception:
                        pass

                post_list.append({
                    'uid': self._get_record_uid(post),
                    'name': post.name,
                    'url_key': post.url_key or '',
                    'content': post.content or '',
                    'teaser': post.teaser or '',
                    'is_published': post.is_published,
                    'published_date': str(post.published_date) if post.published_date else False,
                    'author_id': post.author_id.id if post.author_id else False,
                    'cover_uid': cover_uid,
                    'cover_properties': post.cover_properties or '',
                    'tag_names': [t.name for t in post.tag_ids],
                })

            blog_list.append({
                'uid': self._get_record_uid(blog),
                'name': blog.name,
                'website_id': blog.website_id.id if blog.website_id else False,
                'posts': post_list,
            })

        return {
            'blogs': blog_list,
            'tags': [{'uid': self._get_record_uid(t), 'name': t.name,
                       'category': t.category_id.name if t.category_id else False}
                     for t in tags],
        }

    # ------------------------------------------------------------------ #
    # Events (website_event)                                               #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_events(self, website):
        events = self.env['event.event'].search([
            ('website_published', '=', True),
            '|', ('website_id', '=', website.id), ('website_id', '=', False),
        ])
        event_types = self.env['event.type'].search([])
        event_tags = self.env['event.tag'].search([]) if 'event.tag' in self.env else \
            self.env['event.event'].browse()

        event_list = []
        for event in events:
            tickets = self.env['event.event.ticket'].search(
                [('event_id', '=', event.id)]
            ) if 'event.event.ticket' in self.env else []

            event_list.append({
                'uid': self._get_record_uid(event),
                'name': event.name,
                'date_begin': str(event.date_begin),
                'date_end': str(event.date_end),
                'date_tz': event.date_tz or 'UTC',
                'location': getattr(event, 'location', '') or '',
                'description': event.description or '',
                'website_published': event.website_published,
                'event_type_name': event.event_type_id.name if event.event_type_id else False,
                'tag_names': [t.name for t in getattr(event, 'tag_ids', [])],
                'tickets': [
                    {
                        'name': t.name,
                        'price': t.price,
                        'seats_max': t.seats_max,
                        'sale_available': getattr(t, 'sale_available', True),
                    }
                    for t in tickets
                ],
            })

        return {
            'events': event_list,
            'event_types': [{'name': et.name} for et in event_types],
            'event_tags': [{'name': t.name, 'category': getattr(t, 'category_id', False) and
                             t.category_id.name or False} for t in event_tags],
        }

    # ------------------------------------------------------------------ #
    # Shop / eCommerce (website_sale)                                      #
    # ------------------------------------------------------------------ #
    @api.model
    def _export_shop(self, website, attachment_uid_map):
        domain = [
            ('is_published', '=', True),
            '|', ('website_id', '=', website.id), ('website_id', '=', False),
        ]
        products = self.env['product.template'].search(domain)
        categories = self.env['product.public.category'].search([])
        attributes = self.env['product.attribute'].search([])

        product_list = []
        for tmpl in products:
            # Collect images
            image_uids = []
            for img in getattr(tmpl, 'product_template_image_ids', []):
                if img.image_1920:
                    att_uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'product_img/{img.id}'))
                    # Fake attachment wrapper for _serialize_attachments
                    class _FakeAtt:
                        id = img.id
                        datas = img.image_1920
                        name = f'product_img_{img.id}.png'
                        mimetype = 'image/png'
                        url = ''
                        checksum = ''
                        res_model = 'product.template'
                        res_id = tmpl.id
                    attachment_uid_map[att_uid] = _FakeAtt()
                    image_uids.append(att_uid)

            product_list.append({
                'uid': self._get_record_uid(tmpl),
                'default_code': tmpl.default_code or '',
                'name': tmpl.name,
                'description_sale': tmpl.description_sale or '',
                'list_price': tmpl.list_price,
                'is_published': tmpl.is_published,
                'website_id': tmpl.website_id.id if tmpl.website_id else False,
                'public_categ_names': [c.name for c in getattr(tmpl, 'public_categ_ids', [])],
                'attribute_lines': [
                    {
                        'attribute_name': line.attribute_id.name,
                        'value_names': [v.name for v in line.value_ids],
                    }
                    for line in getattr(tmpl, 'attribute_line_ids', [])
                ],
                'image_uids': image_uids,
            })

        return {
            'products': product_list,
            'public_categories': [
                {'uid': self._get_record_uid(c), 'name': c.name,
                 'parent_name': c.parent_id.name if c.parent_id else False}
                for c in categories
            ],
            'attributes': [
                {'name': a.name,
                 'values': [v.name for v in a.value_ids]}
                for a in attributes
            ],
        }

    # ------------------------------------------------------------------ #
    # Module check (cached)                                                #
    # ------------------------------------------------------------------ #
    @api.model
    def _module_installed(self, module_name):
        return bool(
            self.env['ir.module.module'].sudo().search(
                [('name', '=', module_name), ('state', '=', 'installed')], limit=1
            )
        )

    # ------------------------------------------------------------------ #
    # ZIP builder                                                          #
    # ------------------------------------------------------------------ #
    @api.model
    def _build_manifest(self, website_data, scope, attachment_uid_map):
        counts = {}
        website_list = []
        for wd in website_data:
            c = {
                'pages': len(wd.get('pages', [])),
                'views': len(wd.get('views', [])),
                'menus': len(wd.get('menus', [])),
                'rewrites': len(wd.get('rewrites', [])),
                'assets': len(wd.get('assets', [])),
            }
            if wd.get('blog'):
                c['blogs'] = len(wd['blog'].get('blogs', []))
                c['blog_posts'] = sum(
                    len(b.get('posts', [])) for b in wd['blog'].get('blogs', [])
                )
            if wd.get('events'):
                c['events'] = len(wd['events'].get('events', []))
            if wd.get('shop'):
                c['products'] = len(wd['shop'].get('products', []))
            website_list.append({
                'uid': wd['uid'],
                'name': wd['website']['name'],
                'domain': wd['website']['domain'],
                'counts': c,
            })
            for k, v in c.items():
                counts[k] = counts.get(k, 0) + v

        counts['attachments'] = len(attachment_uid_map)

        installed_mods = ['website']
        for mod in ('website_blog', 'website_event', 'website_sale'):
            if self._module_installed(mod):
                installed_mods.append(mod)

        return {
            'module': 'export_import_web',
            'module_version': '19.0.1.0.0',
            'odoo_version': odoo.release.version[:4],  # '19.0'
            'websites': website_list,
            'installed_modules': installed_mods,
            'counts': counts,
            'created_at': fields.Datetime.now().isoformat(),
            'checksums': {},  # filled after ZIP bytes are known
        }

    @api.model
    def _build_zip(self, website_data, attachments_json, media_files, manifest):
        buf = io.BytesIO()
        checksums = {}

        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for wd in website_data:
                uid = wd['uid']

                def _write(path, data):
                    json_bytes = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
                    checksums[path] = hashlib.sha256(json_bytes).hexdigest()
                    zf.writestr(path, json_bytes)

                _write(f'websites/{uid}/website.json', wd['website'])
                _write(f'websites/{uid}/pages.json', wd.get('pages', []))
                _write(f'websites/{uid}/views.json', wd.get('views', []))
                _write(f'websites/{uid}/menus.json', wd.get('menus', []))
                _write(f'websites/{uid}/rewrites.json', wd.get('rewrites', []))
                _write(f'websites/{uid}/assets.json', wd.get('assets', []))

                if wd.get('blog') is not None:
                    _write(f'websites/{uid}/blog.json', wd['blog'])
                if wd.get('events') is not None:
                    _write(f'websites/{uid}/events.json', wd['events'])
                if wd.get('shop') is not None:
                    _write(f'websites/{uid}/shop.json', wd['shop'])

            # Shared attachment metadata
            att_json_bytes = json.dumps(
                attachments_json, ensure_ascii=False, default=str
            ).encode('utf-8')
            checksums['data/attachments.json'] = hashlib.sha256(att_json_bytes).hexdigest()
            zf.writestr('data/attachments.json', att_json_bytes)

            # Media files
            for zip_path, raw_bytes in media_files.items():
                zf.writestr(zip_path, raw_bytes)

            # Write manifest last with checksums
            manifest['checksums'] = checksums
            zf.writestr('manifest.json', json.dumps(
                manifest, ensure_ascii=False, default=str, indent=2
            ).encode('utf-8'))

        return buf.getvalue()
