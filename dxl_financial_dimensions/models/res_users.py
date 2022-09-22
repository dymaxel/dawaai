# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    bu = fields.Many2many('account.analytic.group', string="BU", domain="[('parent_id', '=', False)]")
