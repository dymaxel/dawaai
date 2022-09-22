# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    reconcile_invoice_ids = fields.One2many('account.payment.reconcile', 'payment_id', string="Invoices", copy=False)

    @api.onchange('partner_id', 'payment_type', 'partner_type')
    def _onchange_partner_id(self):
        res = super(AccountPayment, self)._onchange_partner_id()
        if not self.partner_id:
            return res
        partner_id = self.partner_id
        self.reconcile_invoice_ids = [(5,)]
        move_type = {'outbound': 'in_invoice', 'inbound': 'out_invoice', 'transfer': ''}
        moves = self.env['account.move'].sudo().search([('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'), ('amount_residual', '>', 0), ('type', '=', move_type[self.payment_type])])
        vals = []
        for move in moves:
            vals.append((0, 0, {
                'payment_id': self.id,
                'invoice_id': move.id,
                'amount_untaxed': move.amount_untaxed,
                'amount_tax': move.amount_tax,
                'currency_id': move.currency_id.id,
                'amount_total': move.amount_residual,
            }))
        self.reconcile_invoice_ids = vals
        self.partner_id = partner_id.id
        return res

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        self.amount = sum(self.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('amount_paid'))

    def post(self):
        res = super(AccountPayment, self).post()
        if self.env.context.get('active_model') == 'account.move':
            return res
        for payment in self:
            move_lines = self.env['account.move.line']
            invoice_ids = payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('invoice_id')
            invoice_move = invoice_ids.mapped('line_ids').filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            payment_move = payment.move_line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            move_lines |= (invoice_move + payment_move)
            if move_lines:
                move_lines.auto_reconcile_lines()
        return res

class AccountPaymentReconcile(models.Model):
    _name = 'account.payment.reconcile'

    payment_id = fields.Many2one('account.payment')
    reconcile = fields.Boolean(string="Select")
    invoice_id = fields.Many2one('account.move', string="Bill Number")
    currency_id = fields.Many2one('res.currency')
    amount_total = fields.Monetary(string='Subtotal With Tax')
    amount_untaxed = fields.Monetary(string='Subtotal W/O Tax')
    amount_tax = fields.Monetary(string='Taxes Amount')
    amount_paid = fields.Monetary(string="Amount Paid")
    it_wht_amount = fields.Monetary(string="IT WHT Amount", compute='_compute_wht_amount', store=True, readonly=True)
    st_wht_amount = fields.Monetary(string="ST WHT Amount", compute='_compute_wht_amount', store=True, readonly=True)

    @api.depends('amount_paid', 'payment_id.tds_tax_id', 'payment_id.sales_tds_tax_id')
    def _compute_wht_amount(self):
        for line in self:
            line.it_wht_amount = line.amount_paid * line.payment_id.tds_tax_id.amount / 100
            total_per = line.amount_paid / line.amount_total * 100
            tax_to_per = (line.amount_tax/100.0)/100.0*line.payment_id.sales_tds_tax_id.amount
            final = total_per * tax_to_per
            line.st_wht_amount = final
