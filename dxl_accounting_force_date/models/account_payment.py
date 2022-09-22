# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        if not active_ids:
            return rec
        invoices = self.env['account.move'].browse(active_ids)
        invoice = invoices.filtered(lambda x: x.type == 'out_invoice')
        if invoice and invoice[0].dxl_payment_date:
            rec['payment_date'] = invoice.dxl_payment_date
        return rec
