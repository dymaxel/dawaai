# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountGeneralLedgerReport(models.AbstractModel):
    _inherit = "account.general.ledger"

    filter_account = True
    filter_partner = True

    @api.model
    def _do_query(self, options_list, expanded_account=None, fetch_lines=True):
        accounts_results, taxes_results = super(AccountGeneralLedgerReport, self)._do_query(options_list, expanded_account=expanded_account, fetch_lines=fetch_lines)
        new_res = []
        options = options_list[0]
        if options.get('account_ids'):
            for account_id, dummy in accounts_results:
                if account_id.id in options.get('account_ids'):
                    new_res.append((account_id, dummy))
            accounts_results = new_res
        return accounts_results, taxes_results
