# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    platform_id = fields.Char('Platform ID', copy=False)
    platform_po_name = fields.Char('Platform Name', copy=False)

class PurchaseOrderQueue(models.Model):
    _name = 'purchase.order.queue'
    _order = 'create_date desc'
    _description = "Purchase Order Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done'), ('cancel', 'Cancelled')], tracking=True, default='draft')
    log_ids = fields.One2many('purchase.order.log', 'purchase_order_queue_id')
    ex_purchase_order_id = fields.Char('Platform ID', readonly=True)
    odoo_record_id = fields.Many2one('purchase.order', readonly=True)

    name = fields.Char('Name')
    partner_id = fields.Char('Customer')
    date_planned = fields.Char('Receipt Date')
    payment_term_id = fields.Char('Payment Terms')
    picking_type_id = fields.Char('Deliver To')
    order_line = fields.One2many('purchase.order.queue.line', 'purchase_order_queue_id')

    def get_product_by_platform(self, ex_product_id):
        return self.env['product.product'].sudo().search([('ex_product_id', '=', ex_product_id)])

    def get_partner_by_platform(self, ex_partner_id):
        partner = self.env['res.partner'].sudo().search([('ex_partner_id', '=', ex_partner_id)])
        return partner and partner.id or False

    def prepare_purchase_order_data(self):
        order_line = []
        for line in self.order_line:
            taxes_ids = []
            odoo_product_id = self.get_product_by_platform(int(line.product_id))
            if line.taxes_id:
                taxes_ids.append(int(line.taxes_id))
            order_line.append((0, 0, {
            	'name': odoo_product_id.name,
                'product_id': odoo_product_id and odoo_product_id.id,
                'price_unit': line.price_unit,
                'product_uom': int(line.product_uom),
                'product_qty': line.product_qty,
                'taxes_id': [(6, 0, taxes_ids)],
            }))
        return {
        	'name': 'New',
            'platform_po_name': self.name,
            'partner_id': self.get_partner_by_platform(self.partner_id),
            'date_planned': self.date_planned,
            'payment_term_id': int(self.payment_term_id),
            'picking_type_id': int(self.picking_type_id),
            'ex_purchase_order_id': self.ex_purchase_order_id,
            'platform_po_name': self.name,
            'order_line': order_line,
        }

    def check_order_data(self):
        state = True
        wrong_product = []
        try:
            int(self.payment_term_id)
            int(self.picking_type_id)
        except ValueError as ve:
            self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': ve})
            return False
        if not self.partner_id:
            self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': 'Customer is required!'})
            state = False
        if self.partner_id and not self.env['res.partner'].sudo().search([('ex_partner_id', '=', self.partner_id)]):
            self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': 'Partner does not exist with ID '+self.partner_id})
            state = False
        if self.payment_term_id and not self.env['account.payment.term'].sudo().search([('id', '=', self.payment_term_id)]):
            self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': 'Payment Terms does not exist with ID  '+self.payment_term_id})
            state = False
        if self.picking_type_id and not self.env['stock.picking.type'].sudo().search([('id', '=', self.picking_type_id)]):
            self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': 'Picking Type does not exist with ID  '+self.picking_type_id})
            state = False   
        for line in self.order_line:
            if not self.get_product_by_platform(line.product_id):
                wrong_product.append(line.product_id)
        if wrong_product:
            self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': 'Order Line Product does not exist with IDs '+ str(wrong_product)})
            state = False
        return state

    @api.model
    def create(self, vals):
        order_line = []
        if vals.get('order_line'):
            for line in vals.get('order_line'):
                order_line.append((0, 0, line))
            vals['order_line'] = order_line
        if 'id' in vals:
            vals.update({'ex_purchase_order_id': vals.get('id')})
        return super(PurchaseOrderQueue, self).create(vals)

    def action_run_queue_mannually(self):
        if not self.check_order_data():
            self.write({'state': 'failed'})
            return False
        po_data = self.prepare_purchase_order_data()
        po = self.env['purchase.order'].sudo().search([('ex_purchase_order_id', '=', self.ex_purchase_order_id)])
        if not po:
            try:
                po_id = self.env['purchase.order'].sudo().create(po_data)
                if po_id:
                    self.write({'odoo_record_id': po_id, 'state': 'done'})
                    self.odoo_record_id = po_id.id
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': ve})
        else:
            try:
                po.sudo().write(po_data)
                self.write({'odoo_record_id': po.id, 'state': 'done'})
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': ve})
        return True

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        """
        self.env['purchase.order.log'].sudo().create({'purchase_order_queue_id': self.id, 'name': 'Queue is cancelled by ' + self.env.user.name})
        self.write({'state': 'cancel'})

    def run_purchase_order_queue(self):
        for queue in self.search([('state', '=', 'draft')]).sorted('id'):
            queue.action_run_queue_mannually()

class PurchaseOrderQueueLine(models.Model):
    _name = 'purchase.order.queue.line'
    _description = "Purchase Order Queue Line"

    purchase_order_queue_id = fields.Many2one('purchase.order.queue')
    product_id = fields.Char('Product')
    price_unit = fields.Float('Unit Price')
    product_uom = fields.Char('Unit of Measure')
    product_qty = fields.Char('Quantity')
    taxes_id = fields.Char('Taxes')

class PurchaseOrderLog(models.Model):
    _name = 'purchase.order.log'
    _order = 'create_date desc'

    purchase_order_queue_id = fields.Many2one('purchase.order.queue')
    name = fields.Char('Description')
