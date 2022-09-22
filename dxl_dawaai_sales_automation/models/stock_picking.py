# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # def action_done(self):
    #     res = super(StockPicking, self).action_done()
    #     move_lines = self.env['account.move.line']
    #     # Create auto credit note on delivery return
    #     for pick in self.filtered(lambda x: x.picking_type_id.code == 'incoming' and x.sale_id):
    #         move = pick.sale_id.invoice_ids
    #         move._reverse_moves([{'date': fields.Date.today(), 'ref': _('Reversal of %s') % move.name}], cancel=False)
    #     return res

    def action_done(self):
        res = super(StockPicking, self).action_done()
        for pick in self:
            account_move_lines = []
            customer_invoice = self.env['account.move']
            for move in pick.move_lines.filtered(lambda x: x.picking_type_id.code == 'incoming' and x.sale_line_id):
                customer_invoice = move.sale_line_id.order_id.invoice_ids.filtered(lambda x: x.type == 'out_invoice')
                account_move_lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': move.quantity_done,
                    'price_unit': move.sale_line_id.price_unit,
                    'discount': move.sale_line_id.discount,
                    'sale_line_ids': [(6, 0, move.sale_line_id.ids)],
                    'tax_ids': [(6, 0, move.sale_line_id.tax_id.ids)],
                }))
            if customer_invoice:
                credit_note = self.env['account.move'].with_context(default_type='out_invoice').create({
                    'type': 'out_refund',
                    'partner_id': customer_invoice.partner_id.id,
                    'currency_id': customer_invoice.currency_id.id,
                    'invoice_date': customer_invoice.invoice_date,
                    'reversed_entry_id': customer_invoice.id,
                    'ref': 'Reversal of ' + customer_invoice.name,
                    'invoice_line_ids': account_move_lines
                })
        return res
