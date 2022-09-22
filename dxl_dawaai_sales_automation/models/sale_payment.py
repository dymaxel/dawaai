# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SalePayment(models.Model):
    _name = 'sale.payment'
    _description = "Sale Payment"

    journal_id = fields.Many2one('account.journal', string="Payment Method", required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount', required=True)
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    dxl_payment_date = fields.Datetime('Payment Date')

    @api.model
    def create(self, vals):
        res = super(SalePayment, self).create(vals)
        for payment in res.filtered(lambda x: x.journal_id.type == 'bank'):
            payment_vals = payment.sale_order_id._prepare_payment_data(payment)
            sale_payment = self.env['account.payment'].create(payment_vals)
            sale_payment.sudo().post()
            move_lines = self.env['account.move.line'].search([('payment_id', '=', sale_payment.id)])
            move_lines.write({'sale_ref': payment.sale_order_id.name})
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.One2many('sale.payment', 'sale_order_id', string="Payments", copy=False)

    def _prepare_payment_data(self, payment):
        exchange_rate = self.env['res.currency']._get_conversion_rate(self.company_id.currency_id, self.currency_id, self.company_id, self.date_order)
        currency_amount = payment.amount * (1.0 / exchange_rate)
        payment_dict = {
           'payment_type': 'inbound',
           'partner_id': self.partner_id and self.partner_id.id,
           'partner_type': 'customer',
           'journal_id': payment.journal_id and payment.journal_id.id,
           'company_id': self.company_id and self.company_id.id,
           'currency_id':self.pricelist_id.currency_id.id,
           'payment_date': payment.dxl_payment_date,
           'amount': currency_amount,
           'sale_order_id': self.id,
           'name': _("Payment") + " - " + self.name,
           'communication': self.name,
           'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id
        }
        return payment_dict

    # @api.model
    # def create(self, vals):
    #     sale = super(SaleOrder, self).create(vals)
    #     if sale.payment_ids:
    #         for payment in sale.payment_ids.filtered(lambda x: x.journal_id.type == 'bank'):
    #             payment_vals = sale._prepare_payment_data(payment)
    #             sale_payment = self.env['account.payment'].create(payment_vals)
    #             sale_payment.sudo().post()
    #             move_lines = self.env['account.move.line'].search([('payment_id', '=', sale_payment.id)])
    #             move_lines.write({'sale_ref': sale.name})
    #     return sale

    def _check_availability(self):
        available = True
        location = self.warehouse_id and self.warehouse_id.out_type_id and self.warehouse_id.out_type_id.default_location_src_id
        if not location:
            return False
        product_list = []
        for line in self.order_line.filtered(lambda x: x.product_id.type == 'product'):
            quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', location.id),
            ])
            available_qty = sum(quants.mapped('quantity'))
            if not quants or (line.product_uom_qty > available_qty):
                available = False
                product_list.append(line.product_id.name)
        if product_list:
            msg = ', '.join(product_list)
            raise ValidationError(_(msg + ' are not available in ' +location.complete_name))
        return available

    def action_confirm(self):
        for sale in self:
            if not sale._check_availability():
                return False
        res = super(SaleOrder, self).action_confirm()
        for sale in self:
            # Create cash payment on sale confirm
            if sale.payment_ids:
                for payment in sale.payment_ids.filtered(lambda x: x.journal_id.type == 'cash'):
                    payment_vals = sale._prepare_payment_data(payment)
                    sale_payment = self.env['account.payment'].create(payment_vals)
                    sale_payment.sudo().post()
                    move_lines = self.env['account.move.line'].search([('payment_id', '=', sale_payment.id)])
                    move_lines.write({'sale_ref': sale.name})

            # Force done delivery
            for picking in sale.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel')):
                for move in picking.move_lines:
                    if move.product_id.tracking != 'none':
                        move._action_assign()
                        for line in move.move_line_ids:
                            line.write({'qty_done': line.product_uom_qty})
                    else:
                        move.write({'quantity_done': move.product_uom_qty})
                picking.action_done()

            # Create Customer Invoice on sale confirm
            invoice = sale._create_invoices()
            invoice.action_post()
            invoice.line_ids.write({'sale_ref': sale.name})

            # Reconcile Invoice with payments
            sale_payment_ids = self.env['account.payment'].search([('sale_order_id', '=', sale.id)])
            move_lines = self.env['account.move.line']
            if invoice and sale_payment_ids.filtered(lambda x: x.state == 'posted' and x.payment_type == 'inbound'):
                invoice_move = sale.invoice_ids.mapped('line_ids').filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
                payment_move = sale_payment_ids.mapped('move_line_ids').filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
                move_lines |= (invoice_move + payment_move) 
                move_lines.auto_reconcile_lines()
        return res

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    _description = "Sale Payment"

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_ref = fields.Char('Sale Reference')
