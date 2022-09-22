# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import format_date


class AccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger"

    def _get_columns_name(self, options):
        super(AccountGeneralLedger, self)._get_columns_name(options)
        return [
            {'name': ''},
            {'name': _('Date'), 'class': 'date'},
            {'name': _('Communication')},
            {'name': _('Partner')},
            {'name': _('Sales Reference')},
            {'name': _('Currency'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'}
        ]

    @api.model
    def _get_aml_line(self, options, account, aml, cumulated_balance):
        res = super(AccountGeneralLedger, self)._get_aml_line(options, account, aml, cumulated_balance)
        nar = False
        new_cols = []
        aml_id = self.env['account.move.line'].browse(aml['id'])
        for col in res['columns']:
            if col.get('class') == 'number' and not nar:
                new_cols.append({'name': aml_id.sale_ref or '', 'title': aml_id.sale_ref or '', 'class': 'whitespace_print'})
                nar = True
            new_cols.append(col)
        res['columns'] = new_cols
        return res

    @api.model
    def _get_account_title_line(self, options, account, amount_currency, debit, credit, balance, has_lines):
        res = super(AccountGeneralLedger, self)._get_account_title_line(options, account, amount_currency, debit, credit, balance, has_lines)
        res['colspan'] = 5
        return res

    @api.model
    def _get_account_total_line(self, options, account, amount_currency, debit, credit, balance):
        res = super(AccountGeneralLedger, self)._get_account_total_line(options, account, amount_currency, debit, credit, balance)
        res['colspan'] = 5
        return res

    @api.model
    def _get_initial_balance_line(self, options, account, amount_currency, debit, credit, balance):
        res = super(AccountGeneralLedger, self)._get_initial_balance_line(options, account, amount_currency, debit, credit, balance)
        res['colspan'] = 5
        return res

    @api.model
    def _get_total_line(self, options, debit, credit, balance):
        res = super(AccountGeneralLedger, self)._get_total_line(options, debit, credit, balance)
        res['colspan'] = 6
        return res
