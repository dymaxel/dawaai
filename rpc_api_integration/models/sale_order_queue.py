# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round
import json

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    platform_id = fields.Char('Platform ID', copy=False)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    platform_id = fields.Char('Platform ID', copy=False)
    platform_so_name = fields.Char('Platform Name', copy=False)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _check_line_unlink(self):
        return False

    def write(self, values):
        lines = self.env['sale.order.line']
        if 'product_uom_qty' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            lines = self.filtered(
                lambda r: r.state == 'sale' and not r.is_expense and float_compare(r.product_uom_qty, values['product_uom_qty'], precision_digits=precision) == 1)
        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        res = super(SaleOrderLine, self).write(values)
        if lines:
            lines._action_launch_stock_rule2(previous_product_uom_qty)
        return res

    def _action_launch_stock_rule2(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            if line.state != 'sale' or not line.product_id.type in ('consu','product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            # if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
            #     continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty
            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)
        return True

class SaleOrderQueue(models.Model):
    _name = 'sale.order.queue'
    _order = 'create_date desc'
    _description = "Sale Order Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done'), ('cancel', 'Cancelled')], tracking=True, default='draft')
    log_ids = fields.One2many('sale.order.log', 'sale_order_queue_id')
    ex_sale_order_id = fields.Char('Platform ID')
    odoo_record_id = fields.Many2one('sale.order', readonly=True)

    name = fields.Char('Name')
    commitment_date = fields.Char('Delivery Date')
    partner_id = fields.Char('Customer')
    payment_term_id = fields.Char('Payment Terms')
    pricelist_id = fields.Char('Pricelist')
    warehouse_id = fields.Char('Warehouse')
    order_line = fields.One2many('sale.order.queue.line', 'sale_order_queue_id')
    plateform_id=fields.Char()

    def get_product_by_platform(self, ex_product_id):
        product = self.env['product.product'].sudo().search([('ex_product_id', '=', ex_product_id)], limit=1)
        return product or False

    def get_partner_by_platform(self, ex_partner_id):
        partner = self.env['res.partner'].sudo().search([('ex_partner_id', '=', ex_partner_id)], limit=1)
        return partner and partner.id or False

    def prepare_sale_order_data(self):
        order_line = []
        for line in self.order_line:
            taxes_ids = []
            odoo_product_id = self.get_product_by_platform(line.product_id)
            if line.tax_id:
                taxes_ids.append(int(line.tax_id))
            order_line.append((0, 0, {
                'name': line.name,
                'product_id': odoo_product_id and odoo_product_id.id,
                'discount': line.discount,
                'price_unit': line.price_unit,
                'product_uom': int(line.product_uom) or False,
                'product_uom_qty': line.product_uom_qty,
                'tax_id': [(6, 0, taxes_ids)],
            }))
        return {
            'ex_sale_order_id': self.ex_sale_order_id,
            'platform_so_name': self.name,
            'partner_id': self.get_partner_by_platform(self.partner_id),
            'pricelist_id': int(self.pricelist_id),
            'payment_term_id': int(self.payment_term_id),
            'warehouse_id': int(self.warehouse_id),
            'commitment_date': False if self.commitment_date == 'null' else self.commitment_date,
            'order_line': order_line,
        }

    @api.model
    def cancel_sale_orders(self, vals):
        order_ids = self.env['sale.order'].sudo().search([('ex_sale_order_id', 'in', vals['cancel_order_ids'])])
        if order_ids:
            order_ids.action_cancel()
        return False

    @api.model
    def create(self, vals):
        order_line = []
        if vals.get('order_line'):
            for line in vals.get('order_line'):
                order_line.append((0, 0, line))
            vals['order_line'] = order_line
        if 'id' in vals:
            vals.update({'ex_sale_order_id': vals.get('id')})
        rec=super(SaleOrderQueue, self).create(vals)
        rec.action_run_queue_mannually()

        return rec

    def check_order_data(self):
        state = True
        wrong_product = []
        try:
            int(self.payment_term_id)
            int(self.pricelist_id)
            int(self.warehouse_id)
        except ValueError as ve:
            print('160 ')
            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': ve})
            return False
        if not self.partner_id:
            print('164 ')

            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Customer is required!'})
            state = False
        if self.partner_id and not self.env['res.partner'].sudo().search([('ex_partner_id', '=', self.partner_id)]):
            print('169 ')
            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Partner does not exist with ID '+self.partner_id})
            state = False
        if self.payment_term_id and not self.env['account.payment.term'].sudo().search([('id', '=', self.payment_term_id)]):
            print('173 ')
            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Payment Terms does not exist with ID  '+self.payment_term_id})
            state = False
        if self.pricelist_id and not self.env['product.pricelist'].sudo().search([('id', '=', self.pricelist_id)]):
            print('177 ')
            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Pricelist does not exist with ID  '+self.pricelist_id})
            state = False
        if self.warehouse_id and not self.env['stock.warehouse'].sudo().search([('id', '=', self.warehouse_id)]):
            print('181 ')
            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Warehouse does not exist with ID  '+self.warehouse_id})
            state = False
        for line in self.order_line:
            print('184 ')
            if not self.get_product_by_platform(line.product_id):
                wrong_product.append(line.product_id)
            if line.product_uom and not self.env['uom.uom'].sudo().search_count([('id', '=', int(line.product_uom))]):
                print('189 ')
                self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'UoM does not exist with ID  ' + line.product_uom})
                state = False
            if line.tax_id and not self.env['account.tax'].sudo().search([('id', '=', line.tax_id)]):
                print('193 ')
                self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Tax does not exist with ID  ' + line.tax_id})
                state = False
            if line.product_uom and not line._check_uom():
                self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'The unit of measure defined on the order line does not belong to the same category than the unit of measure defined on the product. Please correct the unit of measure defined on the order line or on the product, they should belong to the same category.'})
                state = False
            print('199 ')
        if wrong_product:
            self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Order Line Product does not exist with IDs '+ str(wrong_product)})
            state = False
            print('203 ')
        return state

    def action_run_queue_mannually(self):
        if not self.check_order_data():
            self.write({'state': 'failed'})
            return False
        so_data = self.prepare_sale_order_data()
        so = self.env['sale.order'].sudo().search([('ex_sale_order_id', '=', self.ex_sale_order_id)])
        if not so:
            try:
                so_id = self.env['sale.order'].sudo().create(so_data)
                if so_id:
                    self.write({'odoo_record_id': so_id, 'state': 'done'})
                    self.odoo_record_id = so_id.id
                    print('281 ',so_id)
                    so_id.action_confirm()
            except ValueError as ve:
                self.write({'state': 'failed'})
                print('222 ',ve)
                self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': ve})
        else:
            try:
                order_line = so_data.get('order_line')
                tobe_delete = []
                new_line = []
                if order_line:
                    for d1, d2, line in order_line:
                        tobe_delete.append(line.get('product_id'))
                        product_id = line.get('product_id')
                        sale_line_id = self.env['sale.order.line'].sudo().search([('order_id', '=', so.id), ('product_id', '=', product_id)], limit=1)
                        sale_line_id.write({'product_uom': line.get('product_uom'), 'product_uom_qty': float(line.get('product_uom_qty')), 'tax_id': line.get('tax_id')})
                        if not sale_line_id:
                            new_line.append((d1, d2, line))
                so_data.pop('order_line')
                if new_line:
                    so_data['order_line'] = new_line
                so.sudo().write(so_data)
                so_line_ids = so.order_line.filtered(lambda x: x.product_id.id not in tobe_delete).sudo()
                move_ids = self.env['stock.move'].sudo().search([('sale_line_id', 'in', so_line_ids.ids)])
                move_ids._action_cancel()
                move_ids.unlink()
                so_line_ids.sudo().unlink()
                self.write({'odoo_record_id': so.id, 'state': 'done'})
            except ValueError as ve:
                print('248 ',ve)
                self.write({'state': 'failed'})
                self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': ve})
        return True

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        """
        self.env['sale.order.log'].sudo().create({'sale_order_queue_id': self.id, 'name': 'Queue is cancelled by ' + self.env.user.name})
        self.write({'state': 'cancel'})

    def run_sale_order_queue(self, limit=None):
        for queue in self.search([('state', '=', 'draft')], limit=limit).sorted('id'):
            queue.action_run_queue_mannually()

class SaleOrderQueueLine(models.Model):
    _name = 'sale.order.queue.line'
    _description = "Sale Order Queue Line"

    sale_order_queue_id = fields.Many2one('sale.order.queue')
    name = fields.Char('Name')
    product_id = fields.Char('Product')
    discount = fields.Float('Discount')
    price_unit = fields.Float('Unit Price')
    product_uom = fields.Char('Unit of Measure')
    product_uom_qty = fields.Char('Total Quantity')
    tax_id = fields.Char('Taxes')

    def _check_uom(self):
        res = True
        for rec in self:
            new_uom = self.env['uom.uom'].sudo().search([('id', '=', int(rec.product_uom))])
            product_id = self.env['product.product'].sudo().search([('ex_product_id', '=', rec.product_id)])
            if new_uom and (product_id.uom_id.category_id.id != new_uom.category_id.id):
                res = False
        return res

class SaleOrderLog(models.Model):
    _name = 'sale.order.log'
    _order = 'create_date desc'

    sale_order_queue_id = fields.Many2one('sale.order.queue')
    name = fields.Char('Description')
