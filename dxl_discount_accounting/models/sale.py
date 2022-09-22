# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    global_discount = fields.Monetary(string='Discount Amount', readonly=True, compute='_amount_all')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        super(SaleOrder, self)._amount_all()
        for order in self:
            global_discount = 0
            for line in order.order_line:
                global_discount += line.price_subtotal * line.discount / 100.0
            order.update({
                'global_discount': global_discount,
                'amount_total': order.amount_total - global_discount,
            })

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if not line.tax_id:
                price = line.price_unit
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            tax_amt = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            price_subtotal = taxes['total_excluded']
            if 'percent' in line.tax_id.mapped('amount_type'):
                tax = sum(line.tax_id.mapped('amount'))
                price_total = line.price_unit * line.product_uom_qty
                price_excl = price_total - (price_total * tax / (100 + tax))
                global_discount = price_excl * line.discount / 100.0
                price_subtotal = taxes['total_excluded'] + global_discount
            if 'fixed' in line.tax_id.mapped('amount_type'):
                price_subtotal = (line.price_unit * line.product_uom_qty) - tax_amt
                global_discount = price_subtotal * line.discount / 100.0
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': price_subtotal,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'price_subtotal')
    def _product_margin(self):
        super(SaleOrderLine, self)._product_margin()
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            price = line.purchase_price
            global_discount = line.price_subtotal * line.discount / 100.0
            margin = line.price_subtotal - ((price * line.product_uom_qty) + global_discount)
            line.margin = currency.round(margin) if currency else margin
