# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        super(AccountMove, self)._onchange_purchase_auto_complete()
        for line in self.line_ids:
            line.bu = line.purchase_line_id.bu and line.purchase_line_id.bu.id
            line.mob = line.purchase_line_id.mob and line.purchase_line_id.mob.id
            line.toc = line.purchase_line_id.toc and line.purchase_line_id.toc.id
            line.pc = line.purchase_line_id.pc and line.purchase_line_id.pc.id
            line.loc = line.purchase_line_id.loc and line.purchase_line_id.loc.id
            line.fun = line.purchase_line_id.fun and line.purchase_line_id.fun.id

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _domain_bu_id(self):
        level = self.env['analytic.account.level'].search([('name', '=', 'BU')])
        return [('level_id', 'in', level and level.ids),('id', 'in', self.env.user.bu.ids)]

    bu = fields.Many2one('account.analytic.group', string='BU', domain=lambda self: self._domain_bu_id())
    mob = fields.Many2one('account.analytic.group', string='Mode of Business')
    toc = fields.Many2one('account.analytic.group', string='Type of Customers')
    pc = fields.Many2one('account.analytic.group', string='Product Category')
    loc = fields.Many2one('account.analytic.group', string='Location')
    fun = fields.Many2one('account.analytic.group', string='Function')
