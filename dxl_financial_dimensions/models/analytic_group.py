# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountAnalyticGroup(models.Model):
    _inherit = "account.analytic.group"

    level_id = fields.Many2one('analytic.account.level', 'Level')
    level = fields.Many2one('account.level', string='Level Number', related='level_id.level')

    @api.onchange('level_id')
    def onchange_level_id(self):
        groups = []
        if self.level_id:
            groups = self.search([]).filtered(lambda l: l.level_id.level.name == self.level_id.parent_level.name)
            return {'domain': {'parent_id': [('id', 'in', groups and groups.ids or [])]}}

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _domain_bu_id(self):
        level = self.env['analytic.account.level'].search([('name', '=', 'BU')])
        return [('level_id', 'in', level and level.ids), ('id', 'in', self.env.user.bu.ids)]

    bu = fields.Many2one('account.analytic.group', string='BU', domain=lambda self: self._domain_bu_id())
    mob = fields.Many2one('account.analytic.group', string='Mode of Business')
    toc = fields.Many2one('account.analytic.group', string='Type of Customers')
    pc = fields.Many2one('account.analytic.group', string='Product Category')
    loc = fields.Many2one('account.analytic.group', string='Location')
    fun = fields.Many2one('account.analytic.group', string='Function')

class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # COGS METHODS
    # -------------------------------------------------------------------------

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        lines_vals_list = super(AccountMove, self)._stock_account_prepare_anglo_saxon_out_lines_vals()
        for line in lines_vals_list:
            if line.get('product_id') and line.get('account_id'):
                product = self.env['product.product'].browse(line.get('product_id'))
                if product.categ_id.property_account_expense_categ_id.id == line.get('account_id'):
                    move_line = self.env['account.move.line'].search([('move_id', '=', line.get('move_id')), ('product_id', '=', line.get('product_id'))])
                    line['bu'] = move_line.bu and move_line.bu.id
                    line['mob'] = move_line.mob and move_line.mob.id
                    line['toc'] = move_line.toc and move_line.toc.id
                    line['pc'] = move_line.pc and move_line.pc.id
                    line['loc'] = move_line.loc and move_line.loc.id
                    line['fun'] = move_line.fun and move_line.fun.id
                    line['analytic_account_id'] = move_line.analytic_account_id and move_line.analytic_account_id.id
        return lines_vals_list
