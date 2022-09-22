# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    disc_type = fields.Selection([('amt_disc', 'Amount Disc'), ('per_disc', '% Disc')], default='per_disc', required=True)
    dw_discount = fields.Float(string='DW Discont', digits='Discount', default=0.0)
    jit = fields.Boolean('JIT')

    def _add_supplier_to_product(self):
        super(PurchaseOrder, self)._add_supplier_to_product()
        for line in self.order_line:
            seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(),
                    uom_id=line.product_uom)
            if seller and line.price_unit > 0:
                seller.write({'price': line.price_unit})

    def button_confirm(self):
        for order in self:
            if not order.order_line:
                raise ValidationError(_('Please add some items to purchase.'))
        return super(PurchaseOrder, self).button_confirm()

    def print_draft_bill(self):
        data = {}
        if self.picking_ids.filtered(lambda x: x.state != 'done'):
            return self.env.ref('dxl_dawaai_purchase.purchase_draft_bill_report').report_action([], data=data)

    def apply_purchase_discount(self):
        total = sum([line.full_unit_price * line.product_qty for line in self.order_line])
        for line in self.order_line:
            line.disc_type = self.disc_type
            line.total_before_disc = line.full_unit_price * line.product_qty
            # line.dw_discount = self.dw_discount / len(self.order_line)
            line.dw_discount =  line.total_before_disc / total * self.dw_discount if total > 0 else 0.0
            if line.disc_type == 'amt_disc':
                # amt_new_price = line.full_unit_price - line.dw_discount
                amt_new_price = (line.total_before_disc - line.dw_discount) / line.product_qty
                line.price_unit = amt_new_price if amt_new_price > 0 else 0.0
            else:
                per_new_price = line.full_unit_price * (1 - line.dw_discount / 100.0)
                line.price_unit = per_new_price if per_new_price > 0 else 0.0
            line.total_after_disc = line.price_unit * line.product_qty

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    full_unit_price = fields.Float(string='Full Unit Price', digits='Product Price')
    dw_discount = fields.Float(string='DW Discont', digits='Discount', default=0.0)
    total_before_disc = fields.Float(string='Sub Total Before Disc', digits='Discount', default=0.0)
    total_after_disc = fields.Float(string='Sub Total After Disc', digits='Discount', default=0.0)
    disc_type = fields.Selection([('amt_disc', 'Amount Disc'), ('per_disc', '% Disc')], default='per_disc', required=True)

    @api.onchange('disc_type', 'full_unit_price', 'dw_discount', 'product_qty')
    def onchange_disc_type(self):
        for line in self:
            line.total_before_disc = line.full_unit_price * line.product_qty
            if line.disc_type == 'amt_disc':
                amt_new_price = line.full_unit_price - line.dw_discount
                line.price_unit = amt_new_price if amt_new_price > 0 else 0.0
            else:
                per_new_price = line.full_unit_price * (1 - line.dw_discount / 100.0)
                line.price_unit = per_new_price if per_new_price > 0 else 0.0
            line.total_after_disc = line.price_unit * line.product_qty

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()
        if not self.order_id.partner_id:
            return result
        # if self.order_id.partner_id.jit:
        #     product_ids = self.env['product.product'].sudo().search([('jit', '=', True)])
        #     domain = {'domain': {'product_id': [('id', 'in', product_ids.ids)]}}
        #     if result:
        #         return result.update(domain)
        #     return domain
        # else:
        if not self.order_id.partner_id.jit:
            supplier_infos = self.env['product.supplierinfo'].search([('name', '=', self.order_id.partner_id.id)])
            product_ids = self.env['product.product']
            for supplier_info in supplier_infos:
                 product_ids += supplier_info.product_tmpl_id.product_variant_ids
            if result:
                result.update({'domain': {'product_id': [('id', 'in', product_ids.ids)]}})
            return {'domain': {'product_id': [('id', 'in', product_ids.ids)]}}
        return result

    # def _prepare_stock_moves(self, picking):
    #     res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
    #     for re in res:
    #         re['current_mrp'] = self.product_id.mrp
    #         re['new_mrp'] = self.product_id.mrp
    #     return res

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        super(PurchaseOrderLine, self)._onchange_quantity()
        if not self.product_id:
            return
        self.full_unit_price = self.price_unit
