# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dxl_delivery_date = fields.Datetime('Delivery Date')
    dxl_invoice_date = fields.Datetime('Delivery Date')
    # dxl_payment_date = fields.Datetime('Payment Date')

    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.dxl_invoice_date:
            invoice_vals.update({
                'invoice_date': self.dxl_invoice_date,
                # 'dxl_payment_date': self.dxl_invoice_date,
            })
        return invoice_vals

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        if self.order_id.dxl_delivery_date:
            values.update({'date_planned': self.order_id.dxl_delivery_date})
        return values
