# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMoveline(models.Model):
    _inherit = "account.move.line"

    is_discount = fields.Boolean("Is Discount", default=False)

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        result = super(AccountMoveline, self)._get_price_total_and_subtotal_model(price_unit, quantity, discount, currency, product, partner, taxes, move_type)
        if move_type != 'out_invoice':
            return result
        res = {}
        # Compute 'price_subtotal'.
        price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount
        # Compute 'price_total'.
        if taxes:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            tax_amount = sum([tax['amount'] for tax in taxes_res['taxes']])
            res['price_subtotal'] = ((price_unit * quantity) - tax_amount)
            res['price_total'] = taxes_res['total_included']
        else:
            subtotal = quantity * price_unit
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount = fields.Monetary(string='Discount Amount', readonly=True, compute='_compute_amount', store=True)

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            move.global_discount = sum((line.discount * line.price_subtotal / 100 for line in move.invoice_line_ids.filtered(lambda x: not x.exclude_from_invoice_tab)))
            # move.amount_untaxed -= move.amount_tax
            move.amount_total -= move.global_discount

    # @api.depends('global_discount')
    def _onchange_invoice_discount(self):
        for invoice in self:
            existing_lines = invoice.line_ids.filtered(lambda x: x.is_discount)
            existing_lines.credit = 0
            existing_lines.debit = 0
            invoice.line_ids -= existing_lines
            for line in invoice.invoice_line_ids.filtered(lambda x: not x.exclude_from_invoice_tab):
                line.recompute_tax_line = True
                if line.discount > 0:
                    create_method = invoice.env['account.move.line'].new
                    create_method({
                        'name': line.name,
                        'debit': (line.price_subtotal * line.discount / 100) * line.quantity,
                        'credit': 0.0,
                        'quantity': 1.0,
                        'amount_currency': line.amount_currency,
                        'date_maturity': invoice.invoice_date,
                        'move_id': invoice.id,
                        'currency_id': invoice.currency_id.id if invoice.currency_id != invoice.company_id.currency_id else False,
                        'account_id': invoice.company_id.discount_account_id.id,
                        'partner_id': invoice.commercial_partner_id.id,
                        'is_discount': True,
                        'exclude_from_invoice_tab': True,
                    })
            invoice._onchange_recompute_dynamic_lines()

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        res = super(AccountMove, self)._onchange_invoice_line_ids()
        if self.type == 'out_invoice':
            self._onchange_invoice_discount()
        return res

    def _move_autocomplete_invoice_lines_values(self):
        values = super(AccountMove, self)._move_autocomplete_invoice_lines_values()
        discount_lines = []
        line_ids = values.get('line_ids')
        total_discount = 0.0
        if self.type != 'out_invoice':
            return values
        for d1, d2, vals in line_ids:
            discount_amount = 0.0
            if len(vals) > 0 and vals.get('discount', 0) > 0:
                discount_amount = (vals.get('price_subtotal') * vals.get('discount', 0) / 100)
                total_discount += discount_amount
                line_ids.append((0, 0, {
                    'name': vals.get('name') or '',
                    'debit': discount_amount,
                    'credit': 0.0,
                    'move_id': self.id,
                    'quantity': 1.0,
                    'company_id': self.company_id.id,
                    'amount_currency': vals.get('amount_currency'),
                    'date_maturity': False,
                    'always_set_currency_id': vals.get('always_set_currency_id'),
                    'account_id': self.company_id.discount_account_id.id,
                    'partner_id': self.commercial_partner_id.id,
                    'is_discount': True,
                    'exclude_from_invoice_tab': True,
                }))
        for d1, d2, vals in line_ids:
            if len(vals) > 0 and vals.get('exclude_from_invoice_tab', False) and not vals.get('is_discount', False):
                account_id = self.env['account.account'].browse(vals.get('account_id'))
                if account_id.internal_type == 'receivable':
                    vals['debit'] = vals.get('debit') - total_discount

        return values
