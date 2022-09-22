# -*- coding: utf-8 -*-
from odoo import models,fields,api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockMoveLine, self).create(vals_list)
        for vals in vals_list:
            if vals.get('picking_id'):
                picking = self.env['stock.picking'].browse(vals.get('picking_id'))
                if picking.state == 'draft':
                    picking.action_confirm()
        return res
