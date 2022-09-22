# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from openerp import models, fields, api, _
from functools import partial

class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_combo = fields.Boolean('Enable Combo')
    edit_combo = fields.Boolean('Single Click for Edit Combo')
    hide_uom = fields.Boolean('Hide UOM')

class PosOrder(models.Model):
    _inherit="pos.order"

    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        new_order_line = []
        process_line = partial(self.env['pos.order.line']._order_line_fields)
        for order_line in ui_order['lines']:
            if 'combo_ext_line_info' in order_line[2]:
                own_pro_list = [process_line(l) for l in order_line[2]['combo_ext_line_info']] if order_line[2][
                    'combo_ext_line_info'] else False
                if own_pro_list:
                    for own in own_pro_list:
                        own[2]['price_subtotal'] = 0
                        own[2]['price_subtotal_incl'] = 0
                        own[2]['tax_ids'] = [(6, 0, [])]
                        new_order_line.append(own)
                del order_line[2]['combo_ext_line_info']
                new_order_line.append(order_line)
            else:
                del order_line[2]['combo_ext_line_info']
                new_order_line.append(order_line)
        res.update({
            'lines': new_order_line,
        })
        return res

# class ProductTemplate(models.Model):
#     _inherit = "product.template"

#     is_combo = fields.Boolean("Is Combo")
#     product_combo_ids = fields.One2many('product.combo', 'product_tmpl_id')

# class ProductCombo(models.Model):
#     _name = 'product.combo'
#     _description = 'Product Combo'
    
#     product_tmpl_id = fields.Many2one('product.template') 
#     require = fields.Boolean("Required", Help="Don't select it if you want to make it optional")
#     category_id = fields.Many2one('product.category', "Categories")
#     product_ids = fields.Many2many('product.product',string="Products")
#     no_of_items = fields.Integer("No. of Items", default= 1)

#     @api.onchange('require')
#     def onchage_require(self):
#         if self.require:
#             self.category_id = False

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args
        if self._context.get('is_required', False):
            args += [['available_in_pos', '=', True]]
        if self._context.get('category_from_line', False):
            category_id = self.env['product.category'].browse(self._context.get('category_from_line'))
            args += [['categ_id', 'child_of', category_id.id],['available_in_pos', '=', True]]
        return super(ProductProduct, self).name_search(name, args=args, operator='ilike', limit=100)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: