# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_smart = fields.Boolean(string='Dawaai Cash Smart Button')
