# -*- coding: utf-8 -*-
from odoo import fields, models

class StockRule(models.Model):
    _inherit = 'stock.rule'

    is_grn = fields.Boolean('Is GRN')
