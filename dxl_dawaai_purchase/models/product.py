# -*- coding: utf-8 -*-
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # jit = fields.Boolean('JIT')
    mrp = fields.Float('MRP')
    readonly_default_code = fields.Boolean(compute='_compute_readonly_default_code')

    def _compute_readonly_default_code(self):
        for tmpl in self:
            if self.env.user.has_group('dxl_dawaai_purchase.group_edit_product_code'):
                tmpl.readonly_default_code = True
            else:
                tmpl.readonly_default_code = False

class ProductProduct(models.Model):
    _inherit = 'product.product'

    readonly_default_code = fields.Boolean(compute='_compute_readonly_default_code')

    def _compute_readonly_default_code(self):
        for product in self:
            if self.env.user.has_group('dxl_dawaai_purchase.group_edit_product_code'):
                product.readonly_default_code = True
            else:
                product.readonly_default_code = False
