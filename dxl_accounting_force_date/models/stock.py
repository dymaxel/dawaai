# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockMove(models.Model):
    _inherit = "stock.move"

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        if self.sale_line_id and self.sale_line_id.order_id.dxl_delivery_date:
            dxl_delivery_date = self.sale_line_id.order_id.dxl_delivery_date
            return super(StockMove, self.with_context(force_period_date=dxl_delivery_date))._create_account_move_line(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        return super(StockMove, self)._create_account_move_line(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)

    def _create_out_svl(self, forced_quantity=None):
        res = super(StockMove, self)._create_out_svl(forced_quantity=forced_quantity)
        for svl in res:
            if svl.stock_move_id.sale_line_id and svl.stock_move_id.sale_line_id.order_id.dxl_delivery_date:
                self.env.cr.execute('UPDATE stock_valuation_layer SET create_date = %(date)s WHERE id = %(svl_id)s', {'date': svl.stock_move_id.sale_line_id.order_id.dxl_delivery_date, 'svl_id': svl.id})
        return res

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if self.mapped('group_id').sale_id:
            res['dxl_delivery_date'] = self.mapped('group_id').sale_id.dxl_delivery_date
        return res

    def _action_done(self, cancel_backorder=False):
        moves_todo = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in moves_todo.filtered(lambda x: x.sale_line_id and x.sale_line_id.order_id.dxl_delivery_date):
            move.write({'date': move.sale_line_id.order_id.dxl_delivery_date})
            move.move_line_ids.write({'date': move.sale_line_id.order_id.dxl_delivery_date})
        return moves_todo

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    dxl_delivery_date = fields.Datetime('Delivery Date')
