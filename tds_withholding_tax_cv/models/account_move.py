# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_tds_amount(self, payment_id):
        if payment_id and payment_id.tds_tax_id:
            amt = self.amount_total * payment_id.tds_tax_id.amount / 100
            return float_round(amt - 0.001, 2, rounding_method='HALF-UP')
        return 0

# class AccountMoveline(models.Model):
#     _inherit = "account.move.line"

#     tds_tag = fields.Boolean("TDS Tag", default=False)


# class AccountMove(models.Model):
#     _inherit = "account.move"

#     @api.depends(
#         'line_ids.debit',
#         'line_ids.credit',
#         'line_ids.currency_id',
#         'line_ids.amount_currency',
#         'line_ids.amount_residual',
#         'line_ids.amount_residual_currency',
#         'line_ids.payment_id.state', 'tds_tax_id')
#     def _compute_amount(self):
#         super(AccountMove, self)._compute_amount()
#         for move in self:
#             if not move.tds:
#                 move.total_gross = move.amount_untaxed + move.amount_tax
#                 move.tds_amt = 0.0
#                 move.amount_total = move.amount_untaxed + move.amount_tax + move.tds_amt
#                 move.tds_tax_id = False
#             else:
#                 move.total_gross = move.amount_untaxed + move.amount_tax
#                 move.tds_amt = -(move.tds_tax_id.amount * (move.total_gross / 100))
#                 move.amount_total = move.amount_untaxed + move.amount_tax + move.tds_amt
#                 applicable = True
#                 if move.partner_id and move.partner_id.tds_threshold_check and move.tds_tax_id:
#                     applicable = move.check_turnover(move.partner_id.id, move.tds_tax_id.payment_excess,
#                                                      move.total_gross)
#                 if not applicable:
#                     move.tds_amt = 0
#                 if not move.tds:
#                     move.tds_amt = 0.0
#                     move.tds_tax_id = False
#                 move.amount_total = move.amount_untaxed + move.amount_tax + move.tds_amt

#     tds = fields.Boolean('Apply TDS', default=False,
#                          states={'draft': [('readonly', False)]})
#     tds_tax_id = fields.Many2one('account.tax', string='TDS',
#                                  states={'draft': [('readonly', False)]})
#     tds_amt = fields.Monetary(string='TDS Amount',
#                               readonly=True, compute='_compute_amount')
#     total_gross = fields.Monetary(string='Total',
#                                   store=True, readonly=True, compute='_compute_amount')
#     amount_total = fields.Monetary(string='Net Total',
#                                    store=True, readonly=True, compute='_compute_amount')
#     vendor_type = fields.Selection(related='partner_id.company_type', string='Partner Type')
#     display_in_report = fields.Boolean('Display TDS in Report', default=False)

#     def check_turnover(self, partner_id, threshold, total_gross):
#         domain = [('partner_id', '=', partner_id), ('account_id.internal_type', '=', 'payable'),
#                   ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
#         journal_items = self.env['account.move.line'].search(domain)
#         credits = sum([item.credit for item in journal_items])
#         credits += total_gross
#         if credits >= threshold:
#             return True
#         else:
#             return False

#     @api.onchange('tds_tax_id', 'tds')
#     def _onchange_tds_tax_id(self):
#         for invoice in self:
#             applicable = True
#             if invoice.partner_id and invoice.partner_id.tds_threshold_check:
#                 applicable = invoice.check_turnover(invoice.partner_id.id, invoice.tds_tax_id.payment_excess,
#                                                     invoice.total_gross)
#             tax_repartition_lines = invoice.tds_tax_id.invoice_repartition_line_ids.filtered(
#                 lambda x: x.repartition_type == 'tax') if invoice.tds_tax_id else None
#             tds_amount = abs(invoice.tds_amt) if invoice.tds and applicable else 0
#             tds_tax = invoice.tds_tax_id if invoice.tds_tax_id else None
#             credit = 0
#             debit = 0
#             if invoice.type in ['in_invoice', 'out_refund', 'in_receipt']:
#                 credit = tds_amount
#             elif invoice.type in ['out_invoice', 'in_refund', 'out_receipt']:
#                 debit = tds_amount
#             existing_lines = invoice.line_ids.filtered(lambda x: x.tds_tag)
#             existing_lines.credit = 0
#             existing_lines.debit = 0
#             invoice.line_ids -= existing_lines
#             if applicable and tds_amount and tds_tax and tax_repartition_lines:
#                 create_method = invoice.env['account.move.line'].new
#                 create_method({
#                     'name': tds_tax.name,
#                     'debit': debit,
#                     'credit': credit,
#                     'quantity': 1.0,
#                     'amount_currency': tds_amount,
#                     'date_maturity': invoice.invoice_date,
#                     'move_id': invoice.id,
#                     'currency_id': invoice.currency_id.id if invoice.currency_id != invoice.company_id.currency_id else False,
#                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
#                     'partner_id': invoice.commercial_partner_id.id,
#                     'tds_tag': True,
#                     'exclude_from_invoice_tab': True,
#                 })
#             invoice._onchange_recompute_dynamic_lines()

#     @api.onchange('invoice_line_ids')
#     def _onchange_invoice_line_ids(self):
#         res = super(AccountMove, self)._onchange_invoice_line_ids()
#         self._onchange_tds_tax_id()
#         return res


class AccountInvoiceTax(models.Model):
    _inherit = "account.tax"

    tds = fields.Boolean('WHT', default=False)
