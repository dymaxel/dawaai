# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    discount_account_id = fields.Many2one('account.account', related='company_id.discount_account_id', readonly=False, string="Discount Account")
