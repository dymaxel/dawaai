# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.constrains('default_code')
    def _check_duplicate_code(self):
        res = self.search([('default_code', '=', self.default_code), ('default_code', '!=', False)])
        if len(res) > 1:
            raise ValidationError(_('Internal Reference must be unique !'))
