# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    global_discount = fields.Float('Discount', readonly=True)

    def _select(self):
        res = super(AccountInvoiceReport,self)._select()
        select_str = res + """, move.global_discount AS global_discount """
        return select_str

    def _group_by(self):
    	res = super(AccountInvoiceReport,self)._group_by()
    	select_str = res + """, move.global_discount"""
    	return select_str
