# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_account = None

    @api.model
    def _init_filter_account(self, options, previous_options=None):
        if not self.filter_account:
            return

        options['account'] = True
        options['account_ids'] = previous_options and previous_options.get('account_ids') or []
