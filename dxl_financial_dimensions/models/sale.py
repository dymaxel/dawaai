# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _domain_bu_id(self):
        level = self.env['analytic.account.level'].search([('name', '=', 'BU')])
        return [('level_id', 'in', level and level.ids), ('id', 'in', self.env.user.bu.ids)]

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    bu = fields.Many2one('account.analytic.group', string='BU', domain=lambda self: self._domain_bu_id())
    mob = fields.Many2one('account.analytic.group', string='Mode of Business')
    toc = fields.Many2one('account.analytic.group', string='Type of Customers')
    pc = fields.Many2one('account.analytic.group', string='Product Category')
    loc = fields.Many2one('account.analytic.group', string='Location')
    fun = fields.Many2one('account.analytic.group', string='Function')

    def _prepare_invoice_line(self):
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        res.update({
            'bu': self.bu and self.bu.id,
            'mob': self.mob and self.mob.id,
            'toc': self.toc and self.toc.id,
            'pc': self.pc and self.pc.id,
            'loc': self.loc and self.loc.id,
            'fun': self.fun and self.fun.id,
            'analytic_account_id': self.analytic_account_id and self.analytic_account_id.id
        })
        return res
