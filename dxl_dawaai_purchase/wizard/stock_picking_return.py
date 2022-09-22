# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round

class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    pack_qty = fields.Float(string="Pack Qty")
    purchase_uom = fields.Many2one('uom.uom', compute='_compute_purchase_uom', string="Purchase UoM")

    def _compute_purchase_uom(self):
        for line in self:
            if line.move_id.purchase_line_id:
                line.purchase_uom = line.move_id.purchase_line_id.product_uom.id
            else:
            	line.purchase_uom = False

    @api.onchange('pack_qty')
    def _onchange_pack_qty(self):
        if self.pack_qty:
            self.quantity = self.purchase_uom._compute_quantity(self.pack_qty, self.uom_id, rounding_method='HALF-UP')
