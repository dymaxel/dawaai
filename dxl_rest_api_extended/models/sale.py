# -*- coding: utf-8 -*-
from odoo import models,fields,api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    confirm = fields.Boolean(copy=False)

    def write(self, values):
        res = super(SaleOrder, self).write(values)
        if values.get('confirm') == True:
            self.action_confirm()
        return res
