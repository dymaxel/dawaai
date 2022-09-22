# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json

class ProductCategory(models.Model):
    _inherit = 'product.category'

    platform_id = fields.Char('Platform ID', copy=False)

class ProductCategoryQueue(models.Model):
    _name = 'product.category.queue'
    _order = 'create_date desc'
    _description = "Category Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    ex_category_id = fields.Char('Platform ID', readonly=True)
    parent_id = fields.Char('Parent ID')
    odoo_record_id = fields.Many2one('product.category', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done'), ('cancel', 'Cancelled')], tracking=True, default='draft')
    log_ids = fields.One2many('product.category.log', 'category_queue_id')

    def prepare_category_data(self):
        return {
        	'name': self.name,
        	'parent_id': int(self.parent_id) or False,
        	'ex_category_id': self.ex_category_id,
        }

    @api.model
    def create(self, vals):
        if 'id' in vals:
            vals.update({'ex_category_id': vals.get('id')})
        return super(ProductCategoryQueue, self).create(vals)

    def check_category_data(self):
        try:
            int(self.parent_id)
        except ValueError as ve:
            self.env['product.category.log'].sudo().create({'category_queue_id': self.id, 'name': ve})
            return False
        state = True
        if self.parent_id and not self.env['product.category'].sudo().search([('id', '=', self.parent_id)]):
            self.env['product.category.log'].sudo().create({'category_queue_id': self.id, 'name': 'Parent Category does not exist with Odoo ID  '+self.parent_id})
            state = False
        return state

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        """
        self.env['product.category.log'].sudo().create({'category_queue_id': self.id, 'name': 'Queue is cancelled by ' + self.env.user.name})
        self.write({'state': 'cancel'})

    def action_run_queue_mannually(self):
        if not self.check_category_data():
            self.write({'state': 'failed'})
            return
        category_data = self.prepare_category_data()
        category = self.env['product.category'].sudo().search([('ex_category_id', '=', self.ex_category_id)])
        if not category:
            try:
                category_id = self.env['product.category'].sudo().create(category_data)
                if category_id:
                    self.write({'odoo_record_id': category_id, 'state': 'done'})
                    self.odoo_record_id = category_id.id
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['product.category.log'].sudo().create({'category_queue_id': self.id, 'name': ve})
        else:
            try:
                category.sudo().write(category_data)
                self.write({'odoo_record_id': category.id, 'state': 'done'})
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['product.category.log'].sudo().create({'category_queue_id': self.id, 'name': ve})

        return True

    def run_category_queue(self):
        for queue in self.search([('state', '=', 'draft')]).sorted('id'):
            queue.action_run_queue_mannually()

class CategoryLog(models.Model):
    _name = 'product.category.log'
    _order = 'create_date desc'

    category_queue_id = fields.Many2one('product.category.queue')
    name = fields.Char('Description')
