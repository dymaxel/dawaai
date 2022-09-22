# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import AccessError, UserError, ValidationError

class account_payment(models.Model):
    _inherit = "account.payment"

    # tds = fields.Boolean('Apply WHT', default=False)
    tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'), ('excluding', 'Payment Excluding With WHT')], default="default", string="Income Tax Withhold Type")
    tds_tax_id = fields.Many2one('account.tax', string='Incomte Tax Withhold Percentage')
    tds_amt = fields.Monetary(string='Income Tax Withhold Amount', compute='compute_tds_amnt')
    vendor_type = fields.Selection(related='partner_id.company_type', string='Partner Type')

    bill_type = fields.Selection([('bill', 'Bill'), ('non_bill', 'Non Bill')], default="bill", string="Bill Type")
    sales_tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'), ('excluding', 'Payment Excluding With WHT')], default="default", string="Sales Tax Withhold Type")
    sales_tds_tax_id = fields.Many2one('account.tax', string='Sales Tax Withhold Percentage')
    sales_tds_amt = fields.Monetary(string='Sales Tax Withhold Amount', compute='compute_sales_tds_amnt')
    sales_tax_amount=fields.Float()

    @api.onchange('tds_type', 'partner_id')
    def set_default_tds_tax_id(self):
        if self.partner_id.wht_id and self.tds_type == 'including':
            self.tds_tax_id = self.partner_id.wht_id.id
        else:
            self.tds_tax_id = False

    @api.onchange('sales_tds_type', 'partner_id')
    def set_default_sales_tds_tax_id(self):
        if self.partner_id.wht_id and self.sales_tds_type == 'including':
            self.sales_tds_tax_id = self.partner_id.wht_id.id
        else:
            self.sales_tds_tax_id = False


    @api.depends('sales_tds_type', 'sales_tds_tax_id','sales_tax_amount')
    def compute_sales_tds_amnt(self):
        for payment in self:
            payment.sales_tds_amt = 0.0
            if payment.sales_tds_type in ('including', 'excluding') and payment.sales_tds_tax_id and payment.payment_type == 'outbound':
                applicable = True
                if payment.amount:
                    if payment.partner_id and payment.partner_id.tds_threshold_check:
                        applicable = self.check_turnover(self.partner_id.id, self.sales_tds_tax_id.payment_excess, self.amount)
                    if applicable and payment.sales_tds_type in ['excluding', 'including'] and payment.amount and payment.bill_type == 'non_bill':
                        amount = payment.sales_tds_tax_id.amount
                        payment.sales_tds_amt = (payment.amount * amount / 100)
                    if applicable and payment.sales_tds_type == 'including' and payment.bill_type != 'non_bill':
                        payment.sales_tds_amt = sum(payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile == True).mapped('st_wht_amount'))
                if payment.bill_type=='non_bill' :
                    applicable = self.check_turnover(self.partner_id.id, self.sales_tds_tax_id.payment_excess,
                                                     self.sales_tax_amount)

                    if applicable:
                        if payment.sales_tax_amount<0:
                            raise ValidationError('Negative value for sales tax not allowed')
                        amount = payment.sales_tds_tax_id.amount
                        payment.sales_tds_amt = (payment.sales_tax_amount * amount / 100)


    @api.depends('tds_type', 'tds_tax_id', 'amount')
    def compute_tds_amnt(self):
        for payment in self:
            payment.tds_amt = 0.0
            if payment.tds_type in ('including', 'excluding') and payment.tds_tax_id and payment.amount and payment.payment_type == 'outbound':
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, self.amount)
                if applicable and payment.tds_type == 'including':
                    payment.tds_amt = sum(payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile == True).mapped('it_wht_amount'))
                if payment.tds_type in ('including', 'excluding') and payment.tds_tax_id and payment.amount and payment.payment_type == 'outbound':
                    tds_amount = payment.tds_tax_id.amount
                    payment.tds_amt = (payment.amount * tds_amount / 100)

    def check_turnover(self, partner_id, threshold, amount):
        if self.payment_type == 'outbound':
            domain = [('partner_id', '=', partner_id), ('account_id.internal_type', '=', 'payable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            credits = sum([item.credit for item in journal_items])
            credits += amount
            if credits >= threshold:
                return True
            else:
                return False
        elif self.payment_type == 'inbound':
            domain = [('partner_id', '=', partner_id), ('account_id.internal_type', '=', 'receivable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            debits = sum([item.debit for item in journal_items])
            debits += amount
            if debits >= threshold:
                return True
            else:
                return False

    def _prepare_payment_moves(self):
        all_move_vals = super(account_payment, self)._prepare_payment_moves()
        applicable = True
        for payment in self:
            if payment.partner_id and payment.partner_id.tds_threshold_check:
                applicable = payment.check_turnover(payment.partner_id.id, payment.tds_tax_id.payment_excess,
                                                    payment.amount)
            if payment.currency_id == payment.company_id.currency_id:
                # Single-currency.
                currency_id = False
            else:
                # Multi-currencies.
                currency_id = payment.currency_id.id
            tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax')
            sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax')
            if ((payment.tds_type == 'including' and payment.tds_tax_id and payment.tds_amt) or (payment.sales_tds_type == 'including' and payment.sales_tds_tax_id and payment.sales_tds_amt)) and applicable and payment.bill_type != 'non_bill':
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier' and payment.bill_type != 'non_bill':
                    vendor_account = False
                    for rec in all_move_vals[0].get('line_ids'):
                        if payment.tds_type == 'including' or payment.sales_tds_type == 'including':
                            if rec[2]['credit']:
                                rec[2]['credit'] = rec[2]['credit'] - (payment.tds_amt + payment.sales_tds_amt)
                    if payment.tds_tax_id and payment.tds_amt:
                        all_move_vals[0]['line_ids'].append((0, 0, {
                            'name': _('Income Tax Withhold'),
                            'amount_currency': payment.tds_amt,
                            'currency_id': currency_id,
                            'debit': 0,
                            'credit': payment.tds_amt,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.id,
                            'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                            'payment_id': payment.id,
                        }))
                    if payment.sales_tds_tax_id and payment.sales_tds_amt:
                        all_move_vals[0]['line_ids'].append((0, 0, {
                            'name': _('Salse Tax Withhold'),
                            'amount_currency': payment.sales_tds_amt,
                            'currency_id': currency_id,
                            'debit': 0,
                            'credit': payment.sales_tds_amt,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.id,
                            'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                            'payment_id': payment.id,
                        }))

            if ((payment.sales_tds_type in ['excluding', 'including'] and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'non_bill') and not payment.tds_tax_id):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    for rec in all_move_vals[0].get('line_ids'):
                        sales_tds_amt = payment.amount - payment.sales_tds_amt
                        credit_amount = payment.amount if payment.sales_tds_type == "excluding" else sales_tds_amt
                        if rec[2]['debit'] and payment.sales_tds_type == "excluding":
                            rec[2]['debit'] = rec[2]['debit'] + payment.sales_tds_amt
                        if rec[2]['credit'] and payment.sales_tds_type == "including":
                            rec[2]['credit'] = rec[2]['credit'] = credit_amount
                    
                    if payment.sales_tds_tax_id and payment.sales_tds_amt:
                        all_move_vals[0]['line_ids'].append((0, 0, {
                            'name': _('Salse Tax Withhold'),
                            'amount_currency': payment.sales_tds_amt,
                            'debit': 0,
                            'credit': payment.sales_tds_amt,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.id,
                            'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                            'payment_id': payment.id,
                        }))
            if ((payment.tds_type in ['excluding', 'including'] and payment.tds_tax_id and payment.tds_amt and payment.bill_type == 'non_bill') and not payment.sales_tds_tax_id):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    for rec in all_move_vals[0].get('line_ids'):
                        tds_amt = payment.amount - payment.tds_amt
                        credit_amount = payment.amount if payment.tds_type == "excluding" else tds_amt
                        if rec[2]['debit'] and payment.tds_type == "excluding":
                            rec[2]['debit'] = rec[2]['debit'] + payment.tds_amt
                        if rec[2]['credit'] and payment.tds_type == "including":
                            rec[2]['credit'] = rec[2]['credit'] = credit_amount
                    if payment.tds_tax_id and payment.tds_amt:
                        all_move_vals[0]['line_ids'].append((0, 0, {
                            'name': _('Salse Tax Withhold'),
                            'amount_currency': payment.tds_amt,
                            'debit': 0,
                            'credit': payment.tds_amt,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.id,
                            'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                            'payment_id': payment.id,
                        }))
            if ((payment.tds_type in ['excluding', 'including'] and payment.sales_tds_type in ['excluding', 'including'] and payment.tds_tax_id and payment.tds_amt and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'non_bill')):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    for rec in all_move_vals[0].get('line_ids'):
                        if payment.tds_type == 'including' or payment.sales_tds_type == 'including':
                            if rec[2]['credit']:
                                rec[2]['credit'] = rec[2]['credit'] - (payment.tds_amt + payment.sales_tds_amt)
                    if payment.tds_tax_id and payment.tds_amt:
                        all_move_vals[0]['line_ids'].append((0, 0, {
                            'name': _('Income Tax Withhold'),
                            'amount_currency': payment.tds_amt,
                            'currency_id': currency_id,
                            'debit': 0,
                            'credit': payment.tds_amt,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.id,
                            'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                            'payment_id': payment.id,
                        }))
                    if payment.sales_tds_tax_id and payment.sales_tds_amt:
                        all_move_vals[0]['line_ids'].append((0, 0, {
                            'name': _('Salse Tax Withhold'),
                            'amount_currency': payment.sales_tds_amt,
                            'currency_id': currency_id,
                            'debit': 0,
                            'credit': payment.sales_tds_amt,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.id,
                            'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                            'payment_id': payment.id,
                        }))
            return all_move_vals

    def _create_payment_entry(self, amount):
        applicable = True
        if self.partner_id and self.partner_id.tds_threshold_check:
            applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, amount)
        if self.tds_type in ('including', 'excluding') and self.tds_tax_id and self.tds_amt and applicable:
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            invoice_currency = False
            if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
                # if all the invoices selected share the same currency, record the payment in that currency too
                invoice_currency = self.invoice_ids[0].currency_id
            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
            move = self.env['account.move'].create(self._get_move_vals())

            # Write line corresponding to invoice payment
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            counterpart_aml_dict.update({'currency_id': currency_id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

            # Reconcile with the invoices
            payment_difference_handling = 'reconcile'
            payment_difference = self.tds_amt
            writeoff_account_id = self.tds_tax_id and self.tds_tax_id.account_id

            if payment_difference_handling == 'reconcile' and payment_difference:
                writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
                    date=self.payment_date)._compute_amount_fields(payment_difference, self.currency_id,
                                                                   self.company_id.currency_id)
                writeoff_line['name'] = _('Counterpart')
                writeoff_line['account_id'] = writeoff_account_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = aml_obj.create(writeoff_line)
                if counterpart_aml['debit']:
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit']:
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
            self.invoice_ids.register_payment(counterpart_aml)

            # Write counterpart lines
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

            move.post()
            return move
        return super(account_payment, self)._create_payment_entry(amount)
