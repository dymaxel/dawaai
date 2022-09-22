# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json


class ProductBrandQueue(models.Model):
    _name = 'product.brand.queue'
    _order = 'create_date desc'
    _description = "Brand Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    ex_brand_id = fields.Char('Platform ID', readonly=True)
    odoo_record_id = fields.Many2one('product.brand', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done'), ('cancel', 'Cancelled')], tracking=True, default='draft')
    log_ids = fields.One2many('product.brand.log', 'brand_queue_id')

    def prepare_brand_data(self):
        return {
            'name': self.name,
            'ex_brand_id': self.ex_brand_id,
        }

    @api.model
    def create(self, vals):
        if 'id' in vals:
            vals.update({'ex_brand_id': vals.get('id')})
        return super(ProductBrandQueue, self).create(vals)

    def action_run_queue_mannually(self):
        brand_data = self.prepare_brand_data()
        brand = self.env['product.brand'].sudo().search([('ex_brand_id', '=', self.ex_brand_id)])
        if not brand:
            try:
                brand_id = self.env['product.brand'].sudo().create(brand_data)
                if brand_id:
                    self.write({'odoo_record_id': brand_id, 'state': 'done'})
                    self.odoo_record_id = brand_id.id
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['product.brand.log'].sudo().create({'brand_queue_id': self.id, 'name': ve})
        else:
            try:
                brand.sudo().write(brand_data)
                self.write({'odoo_record_id': brand.id, 'state': 'done'})
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['product.brand.log'].sudo().create({'brand_queue_id': self.id, 'name': ve})

        return True

    def run_category_queue(self):
        for queue in self.search([('state', '=', 'draft')]).sorted('id'):
            queue.action_run_queue_mannually()

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        """
        self.env['product.brand.log'].sudo().create({'brand_queue_id': self.id, 'name': 'Queue is cancelled by ' + self.env.user.name})
        self.write({'state': 'cancel'})

class BrandLog(models.Model):
    _name = 'product.brand.log'
    _order = 'create_date desc'

    brand_queue_id = fields.Many2one('product.brand.queue')
    name = fields.Char('Description')
