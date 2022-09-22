# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        # if not self.env.user.has_group('dxl_dawaai_purchase.group_purchase_mrp_approval') and any(move.mrp_state == True and move.quantity_done > 0 for move in self.move_lines):
        #     raise UserError(_('There is difference in Current and New MRP. Please contact your manager.'))
        if self.env.user.has_group('dxl_dawaai_purchase.group_purchase_mrp_approval') and any(move.mrp_state == True and move.quantity_done > 0 for move in self.move_lines):
            for move in self.move_lines.filtered(lambda x: x.mrp_state == True):
                move.product_id.write({'mrp': move.move_line_ids.sorted(key='id')[-1:].new_mrp})
        return super(StockPicking, self).button_validate()

    @api.depends('state', 'is_locked')
    def _compute_show_validate(self):
        super(StockPicking, self)._compute_show_validate()
        is_group = self.env.user.has_group('dxl_dawaai_purchase.group_purchase_mrp_approval')
        for picking in self:
            if not (picking.immediate_transfer) and picking.state == 'draft' or (not is_group and picking.picking_type_code == 'incoming'):
                picking.show_validate = False
            elif picking.state not in ('draft', 'waiting', 'confirmed', 'assigned') or not picking.is_locked or (not is_group and picking.picking_type_code == 'incoming'):
                picking.show_validate = False
            else:
                picking.show_validate = True

    def action_done(self):
        res = super(StockPicking, self).action_done()
        for pick in self:
            account_move_lines = []
            vendor_bill = self.env['account.move']
            for move in pick.move_lines.filtered(lambda x: x.picking_type_id.code == 'outgoing' and x.purchase_line_id):
                vendor_bill = move.purchase_line_id.order_id.invoice_ids.filtered(lambda x: x.type == 'in_invoice')
                account_move_lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': move.quantity_done,
                    'price_unit': move.purchase_line_id.price_unit,
                    'purchase_line_id': move.purchase_line_id.id,
                    'tax_ids': [(6, 0, move.purchase_line_id.taxes_id.ids)]
                }))
            if vendor_bill:
                refund = self.env['account.move'].with_context(default_type='out_invoice').create({
                    'type': 'in_refund',
                    'partner_id': vendor_bill.partner_id.id,
                    'currency_id': vendor_bill.currency_id.id,
                    'invoice_date': vendor_bill.invoice_date,
                    'reversed_entry_id': vendor_bill.id,
                    'ref': 'Reversal of ' + vendor_bill.name,
                    'invoice_line_ids': account_move_lines
                })
        return res
