# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_cash = fields.Monetary(compute='_compute_cash_amount')

    def _compute_cash_amount(self):
        for partner in self:
            aml = self.env['account.move.line'].sudo().search([
                ('account_id.is_smart', '=', True),
                ('partner_id', '=', partner.ids)
            ])
            partner.total_cash = sum(aml.mapped('balance'))

    def open_general_ledger(self):
        account_ids = self.env['account.account'].search([('is_smart', '=', True)])
        return {
            'type': 'ir.actions.client',
            'name': _('General Ledger'),
            'tag': 'account_report',
            'options': {
                'partner_ids': [self.id],
                'account_ids': account_ids.ids,
            },
            'ignore_session': 'both',
            'context': "{'model':'account.general.ledger'}"
        }
