# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AnalyticAccountLevel(models.Model):
    _name = "analytic.account.level"
    _description = "Analytic Account Level"

    name = fields.Char('Name', required=True)
    level = fields.Many2one('account.level', string='Level', required=True)
    parent_level = fields.Many2one('account.parent.level', string='Parent')
    first_level = fields.Boolean('Is First Level')
    last_level = fields.Boolean('Is Last Level')

    @api.onchange('level')
    def onchange_level(self):
        if self.level:
            return {'domain': {'parent_level': [('id', 'in', [val for val in range(1,6) if val < int(self.level)])]}}
            

class AccountLevel(models.Model):
    _name = "account.level"
    _description = "Account Level"

    name = fields.Char(string='Name')


class AccountParentLevel(models.Model):
    _name = "account.parent.level"
    _description = "Account Parent Level"

    name = fields.Char(string='Name')

class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    level_ids = fields.Many2many('analytic.account.level', compute='_compute_level_ids')

    def _compute_level_ids(self):
        for account in self:
            account.level_ids = self.env['analytic.account.level'].search([('last_level', '=', True)])
