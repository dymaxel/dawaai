# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json

class UomUom(models.Model):
    _inherit = 'uom.uom'

    platform_id = fields.Char('Platform ID', copy=False)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    platform_id = fields.Char('Platform ID', copy=False)

    @api.model
    def create(self, vals):
        if vals.get('platform_id'):
            vals['taxes_id'] = False
        return super(ProductTemplate, self).create(vals)

class ProductProductQueue(models.Model):
    _name = 'product.product.queue'
    _order = 'create_date desc'
    _description = "Product Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done'), ('cancel', 'Cancelled')], tracking=True, default='draft')
    log_ids = fields.One2many('product.product.log', 'product_queue_id')
    ex_product_id = fields.Char('Platform ID', readonly=True)
    odoo_record_id = fields.Many2one('product.product', readonly=True)
    type = fields.Char('Product Type')
    categ_id = fields.Char('Product Category')
    default_code = fields.Char('Internal Reference')
    barcode = fields.Char('Barcode')
    standard_price = fields.Float('Cost')
    list_price = fields.Float('Sale Price')
    taxes_id = fields.Char('Tax')
    sale_ok = fields.Char('Can be Sold')
    purchase_ok = fields.Char('Can be Purchased')
    uom_id = fields.Char('Sale Unit of Measure')
    uom_po_id = fields.Char(string='Purchase Unit of Measure')
    invoice_policy = fields.Char(string='Invoicing Policy')
    supplier_taxes_id = fields.Char(string='Vendor Taxes')
    purchase_method = fields.Char(string="Control Policy")
    tracking = fields.Char(string="Tracking")

    class_id = fields.Char(string="Product Classification")
    brand_id = fields.Char(string="Product Brand")
    sku = fields.Char('SKU', copy=False)
    expiry_validation = fields.Integer('Expiry Validation', copy=False)
    pack_size = fields.Char('Pack Size', copy=False)
    strip_size = fields.Char('Strip Size', copy=False)

    def _check_uom(self):
        res = True
        for rec in self:
            product_id = self.env['product.product'].sudo().search([('ex_product_id', '=', rec.ex_product_id)])
            new_uom = self.env['uom.uom'].sudo().browse(int(rec.uom_id))
            updated = product_id.product_tmpl_id.filtered(lambda template: template.uom_id != new_uom)
            done_moves = self.env['stock.move'].sudo().search([('product_id', 'in', updated.with_context(active_test=False).mapped('product_variant_ids').ids)], limit=1)
            if done_moves:
                res = False
        return res

    def get_product_categ(self, paltform_id):
        return self.env['product.category'].sudo().search([('id', '=', paltform_id)], limit=1)

    def prepare_product_data(self):
        categ_id = self.get_product_categ(self.categ_id)
        brand_id = self.env['product.brand'].search([('ex_brand_id', '=', self.brand_id)])
        product_data = {
            'name': self.name,
            'ex_product_id': self.ex_product_id,
            'type': self.type,
            'categ_id':  categ_id and categ_id.id or False,
            'default_code': self.default_code,
            'barcode': self.barcode or False,
            'standard_price': self.standard_price,
            'lst_price': self.list_price,
            'sale_ok': self.sale_ok,
            'purchase_ok': self.purchase_ok,
            'uom_id': int(self.uom_id),
            'uom_po_id': int(self.uom_po_id),
            'purchase_method': self.purchase_method,
            'class_id': self.class_id,
            'brand_id': brand_id and brand_id.id,
            'sku': self.sku,
            'expiry_validation': self.expiry_validation,
            'pack_size': self.pack_size,
            'strip_size': self.strip_size,
            'tracking': self.tracking or 'none',
        }
        print('PPPPPPPPPP', product_data)
        if self.supplier_taxes_id:
            product_data['supplier_taxes_id'] = [(6, 0, [int(self.supplier_taxes_id)])]
        if self.taxes_id:
            product_data['taxes_id'] = [(6, 0, [int(self.taxes_id)])]
        return product_data

    def check_product_data(self):
        state = True
        try:
            int(self.uom_id)
            int(self.uom_po_id)
            int(self.supplier_taxes_id)
            int(self.taxes_id)
        except ValueError as ve:
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': ve})
            return False
        if self.categ_id and not self.env['product.category'].sudo().search([('id', '=', self.categ_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Product Category does not exist with Odoo ID '+self.categ_id})
            state = False
        if self.uom_id and not self.env['uom.uom'].sudo().search([('id', '=', self.uom_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Unit of Measures does not exist with ID '+self.uom_id})
            state = False
        if self.uom_po_id and not self.env['uom.uom'].sudo().search([('id', '=', self.uom_po_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Unit of Measures does not exist with ID '+self.uom_po_id})
            state = False
        if self.supplier_taxes_id and not self.env['account.tax'].sudo().search([('id', '=', self.supplier_taxes_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Account Tax does not exist with ID '+self.supplier_taxes_id})
            state = False
        if self.taxes_id and not self.env['account.tax'].sudo().search([('id', '=', self.taxes_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Account Tax does not exist with ID '+self.taxes_id})
            state = False
        if self.barcode and self.env['product.product'].sudo().search([('barcode', '=', self.barcode), ('ex_product_id', '!=', self.ex_product_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Barcode already exist : '+self.barcode})
            state = False
        if self.sale_ok not in ('True', 'False') or self.purchase_ok not in ('True', 'False'):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Wrong Value in Purchase OK or Sale OK, Please set True or False'})
            state = False
        if not self._check_uom():
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'You cannot change the unit of measure as there are already stock moves for this product. If you want to change the unit of measure, you should rather archive this product and create a new one.'})
            state = False
        if self.class_id and not self.env['product.classification'].sudo().search([('id', '=', int(self.class_id))]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Product Classification does not exist with ID' + self.class_id})
            state = False
        if self.brand_id and not self.env['product.brand'].sudo().search([('ex_brand_id', '=', self.brand_id)]):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Product brand does not exist with ID' + self.brand_id})
            state = False
        if self.tracking and self.tracking not in ('lot', 'serial', 'none'):
            self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Wrong tracking ' + self.tracking})
            state = False
        return state

    def action_run_queue_mannually(self):
        if not self.check_product_data():
            self.write({'state': 'failed'})
            return False
        product_data = self.prepare_product_data()
        product = self.env['product.product'].sudo().search([('ex_product_id', '=', self.ex_product_id)])
        if not product:
            try:
                product_id = self.env['product.product'].sudo().create(product_data)
                if product_id:
                    self.write({'odoo_record_id': product_id, 'state': 'done'})
                    self.odoo_record_id = product_id.id
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': ve})
        else:
            try:
                product.sudo().write(product_data)
                self.write({'odoo_record_id': product.id, 'state': 'done'})
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': ve})

        return True

    @api.model
    def create(self, vals):
        if 'id' in vals:
            vals.update({'ex_product_id': vals.get('id')})
        rec= super(ProductProductQueue, self).create(vals)
        rec.action_run_queue_mannually()
        return rec

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        """
        self.env['product.product.log'].sudo().create({'product_queue_id': self.id, 'name': 'Queue is cancelled by ' + self.env.user.name})
        self.write({'state': 'cancel'})

    def run_product_queue(self):
        for queue in self.search([('state', '=', 'draft')]).sorted('id'):
            queue.action_run_queue_mannually()

class ProductLog(models.Model):
    _name = 'product.product.log'
    _order = 'create_date desc'

    product_queue_id = fields.Many2one('product.product.queue')
    name = fields.Char('Description')
