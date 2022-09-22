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

import xlwt
from lxml import etree
from datetime import datetime
from odoo import models, fields, api, _
# from odoo.osv.orm import setup_modifiers
from odoo.exceptions import Warning


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        for order_line in self.order_line:
            if order_line.combo_product_sequence:
                stock_id = self.env['stock.picking'].search([('combo_product_seq', '=', order_line.combo_product_sequence)])
                for each_stock in stock_id:
                    each_stock.write({'sale_id': self.id})
                    for each_line in each_stock.move_lines:
                        each_line.write({'product_uom_qty': order_line.product_uom_qty,})
        return result

    @api.model
    def create(self, vals):
        result = super(SaleOrder, self).create(vals)
        for order_line in result.order_line:
            if order_line.combo_product_sequence:
                stock_id = self.env['stock.picking'].search([('combo_product_seq', '=', order_line.combo_product_sequence)])
                for each_stock in stock_id:
                    each_stock.write({'sale_id': result.id})
                    for each_line in each_stock.move_lines:
                        each_line.write({'product_uom_qty': order_line.product_uom_qty,})
        return result

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for order in self.order_line:
            if order.combo_product_sequence:
                stock_id = self.env['stock.picking'].search([('combo_product_seq', '=', order.combo_product_sequence)])
                if stock_id:
                    for each_stock in stock_id:
                        each_stock.write({'sale_id': self.id})
                        if each_stock.state == 'done':
                            pass
                        else:
                            raise Warning(_('You can not confirm the order because child products picking are not done'))
                        move_id = self.env['stock.move'].search([('picking_id', '=', each_stock.id)])
                        for each_product in each_stock.move_lines:
                            if 1 in each_product.product_id.route_ids.ids:
                                for each_move in move_id:
                                    values = each_move._prepare_procurement_values()
                                    origin = (each_move.group_id and each_move.group_id.name or (
                                                each_move.origin or each_move.picking_id.name or "/"))
                                    self.env['procurement.group'].run(each_move.product_id, each_move.product_uom_qty,
                                                                      each_move.product_uom,
                                                                      each_move.location_id,
                                                                      each_move.rule_id and each_move.rule_id.name or "/",
                                                                      origin,
                                                                      values)
        return result


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_combo = fields.Boolean(string='Enable Combo')
    edit_combo = fields.Boolean(string='Single Click for Edit Combo')

    @api.onchange('enable_combo', 'edit_combo')
    def _validate_combo(self):
        if not self.enable_combo:
            res = self.env['product.template'].search([('is_combo','=', True)])
            for line in res:
                line.write({'is_combo': False})

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
                enable_combo=get_param('aspl_sale_combo_ee.enable_combo'),
                # edit_combo=get_param('aspl_sale_combo_ee.edit_combo'),

            )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('aspl_sale_combo_ee.enable_combo', self.enable_combo)
        # set_param('aspl_sale_combo_ee.edit_combo', self.edit_combo)


class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = 'Product Combo'

    product_tmplte_id = fields.Many2one('product.template')
    require = fields.Boolean("Required")
    category_id = fields.Many2one('product.category', "Categories")
    product_ids = fields.Many2many('product.product', string="Products")
    no_of_items = fields.Integer("No. of Items", default=1)
    select_default = fields.Boolean(string='Select Default')

    @api.onchange('require')
    def onchage_require(self):
        if self.require:
            self.category_id = False
            self.select_default = False


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_combo = fields.Boolean("Is Combo")
    product_combo_ids = fields.One2many('product.combo', 'product_tmplte_id')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        if not self.env['ir.config_parameter'].sudo().get_param('aspl_sale_combo_ee.enable_combo'):
            if view_type == 'form':
                doc = etree.XML(res['arch'])
                nodes = doc.xpath("//field[@name='is_combo']")
                for node in nodes:
                    node.set('invisible', '1')
                    # setup_modifiers(node)
                nodes = doc.xpath("//label[@name='combo']")
                for node in nodes:
                    node.set('invisible', '1')
                    # setup_modifiers(node)
                res['arch'] = etree.tostring(doc)
        return res


class SaleOrderLine(models.Model):
    _inherit="sale.order.line"

    is_combo = fields.Boolean(related="product_id.product_tmpl_id.is_combo")
    combo_product_sequence = fields.Char(string='Combo Product Sequence ', compute='compute_combo_seq',store=True)
    is_sequence = fields.Char(string='Sequence')

    @api.depends('combo_product_sequence', 'product_id')
    def compute_combo_seq(self):
        for each in self:
            if each.is_combo:
                if not each.combo_product_sequence and not each.is_sequence:
                    each.combo_product_sequence = self.env['ir.sequence'].next_by_code('combo.product.no')
                    each.is_sequence = each.combo_product_sequence
                else:
                    each.combo_product_sequence = each.is_sequence

    @api.model
    def execute(self, record):
        list1={}
        categ_dict = {}
        selected_product = []
        stock_id = self.env['stock.picking'].search([('combo_product_seq', '=', record.get('sale_order_line'))])
        for each in stock_id:
            for each_product in each.move_lines:
                selected_product.append(each_product.product_id.id)
                if not each_product.is_required:
                    if each_product.product_categ not in categ_dict:
                        categ_dict[each_product.product_categ] = [each_product.product_id.id]
                    else:
                        categ_dict[each_product.product_categ].append(each_product.product_id.id)
        if selected_product and categ_dict:
            list1.update({'selected_product': selected_product, 'categ': [categ_dict]})
        res = self.env['product.product'].browse(record.get('res_id'))
        for combo in res.product_combo_ids:
            if combo.select_default:
                if not stock_id.is_editable:
                    categ_name = self.env['product.category'].browse(combo.category_id.id)
                    for id in combo.product_ids:
                        if 'optional' not in list1:
                            if selected_product:
                                if id.id in selected_product:
                                    list1.update(
                                        {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items, 'selected']]}})
                                else:
                                    list1.update(
                                        {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items]]}})
                            else:
                                list1.update(
                                    {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items]]}})
                            keys = {'keys': [categ_name.name]}
                            items = {categ_name.name: combo.no_of_items}
                        else:
                            if categ_name.name not in list1.get('optional'):
                                if selected_product and id.id in selected_product:
                                    list1['optional'][categ_name.name] = [[id.id, id.name, combo.no_of_items, 'selected']]

                                else:
                                    list1['optional'][categ_name.name] = [[id.id, id.name, combo.no_of_items]]
                                keys.get('keys').append(categ_name.name)
                                items.update({categ_name.name: combo.no_of_items})
                            else:
                                if selected_product and id.id in selected_product:
                                    list1['optional'][categ_name.name].append(
                                        [id.id, id.name, combo.no_of_items, 'selected'])

                                else:
                                    list1['optional'][categ_name.name].append(
                                        [id.id, id.name, combo.no_of_items])
                    list1.update(keys)
                    list1.update(items)
                    for no_item in range(combo.no_of_items):
                        list1['optional'][categ_name.name][no_item].append('selected')

            if not combo.select_default:
                if combo.require:
                    for id in combo.product_ids:
                        if 'required' not in list1:
                            list1['required']=[[id.id,id.name,combo.no_of_items]]
                        else:
                            list1.get('required').append([id.id,id.name,combo.no_of_items])
                else:
                    categ_name = self.env['product.category'].browse(combo.category_id.id)
                    for id in combo.product_ids:
                        if 'optional' not in list1:
                            if selected_product:
                                if id.id in selected_product:
                                    list1.update({'optional':{categ_name.name:[[id.id,id.name,combo.no_of_items, 'selected']]}})
                                else:
                                    list1.update(
                                        {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items]]}})
                            else:
                                list1.update(
                                    {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items]]}})
                            keys={'keys':[categ_name.name]}
                            items={categ_name.name:combo.no_of_items}
                        else:
                            if categ_name.name not in list1.get('optional'):
                                if selected_product and id.id in selected_product:
                                    list1['optional'][categ_name.name]=[[id.id,id.name,combo.no_of_items, 'selected']]

                                else:
                                    list1['optional'][categ_name.name] = [[id.id, id.name, combo.no_of_items]]
                                keys.get('keys').append(categ_name.name)
                                items.update({categ_name.name:combo.no_of_items})
                            else:
                                if selected_product and id.id in selected_product:
                                    list1['optional'][categ_name.name].append([id.id,id.name,combo.no_of_items, 'selected'])

                                else:
                                    list1['optional'][categ_name.name].append(
                                        [id.id, id.name, combo.no_of_items])
                    list1.update(keys)
                    list1.update(items)

            if combo.select_default and stock_id.is_editable:
                if combo.require:
                    for id in combo.product_ids:
                        if 'required' not in list1:
                            list1['required']=[[id.id,id.name,combo.no_of_items]]
                        else:
                            list1.get('required').append([id.id,id.name,combo.no_of_items])
                else:
                    categ_name = self.env['product.category'].browse(combo.category_id.id)
                    for id in combo.product_ids:
                        if 'optional' not in list1:
                            if selected_product:
                                if id.id in selected_product:
                                    list1.update({'optional':{categ_name.name:[[id.id,id.name,combo.no_of_items, 'selected']]}})
                                else:
                                    list1.update(
                                        {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items]]}})
                            else:
                                list1.update(
                                    {'optional': {categ_name.name: [[id.id, id.name, combo.no_of_items]]}})
                            keys={'keys':[categ_name.name]}
                            items={categ_name.name:combo.no_of_items}
                        else:
                            if categ_name.name not in list1.get('optional'):
                                if selected_product and id.id in selected_product:
                                    list1['optional'][categ_name.name]=[[id.id,id.name,combo.no_of_items, 'selected']]

                                else:
                                    list1['optional'][categ_name.name] = [[id.id, id.name, combo.no_of_items]]
                                keys.get('keys').append(categ_name.name)
                                items.update({categ_name.name:combo.no_of_items})
                            else:
                                if selected_product and id.id in selected_product:
                                    list1['optional'][categ_name.name].append([id.id,id.name,combo.no_of_items, 'selected'])
                                else:
                                    list1['optional'][categ_name.name].append(
                                        [id.id, id.name, combo.no_of_items])
                    list1.update(keys)
                    list1.update(items)
        return list1

    @api.model
    def combo_product(self, combo):
        value = {}
        combo_selected = []
        move_line_list = []
        for each_categ in combo.get('combo_product'):
            for each_product in combo.get('combo_product').get(each_categ):
                if each_product not in combo_selected:
                    combo_selected.append(each_product)
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        dest_location_id = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        stock_id = self.env['stock.picking'].search([('combo_product_seq', '=', combo.get('combo_sequence'))])
        order_line = self.env['sale.order.line'].search([('combo_product_sequence', '=', combo.get('combo_sequence'))])
        if stock_id:
            for each_stock in stock_id:
                for each_line in each_stock.move_lines:
                    each_line.unlink()
                for each_categ in combo.get('combo_product'):
                    if each_categ == 'required':
                        for each in combo.get('combo_product').get(each_categ):
                            product_id = self.env['product.product'].browse(each)
                            move_line_list.append((0, 0, {'name': 'Combo Product',
                                                          'product_uom': product_id.uom_id.id,
                                                          'product_categ': each_categ,
                                                          'is_required': True,
                                                          'product_id': each,
                                                          'product_uom_qty': 1,
                                                          'location_dest_id': dest_location_id.id,
                                                          'location_id': picking_type_id.default_location_src_id.id,
                                                          }))
                    else:
                        selected_list = []
                        for each in combo.get('combo_product').get(each_categ):
                            if each not in selected_list:
                                selected_list.append(each)
                        for each_selected_product in selected_list:
                            product_id = self.env['product.product'].browse(each_selected_product)
                            move_line_list.append((0, 0, {'name': 'Combo Product',
                                                          'product_uom': product_id.uom_id.id,
                                                          'product_categ': each_categ,
                                                          'is_required': False,
                                                          'product_id': each_selected_product,
                                                          'product_uom_qty': 1,
                                                          'location_dest_id': dest_location_id.id,
                                                          'location_id': picking_type_id.default_location_src_id.id,
                                                         }))
                each_stock.move_lines = move_line_list
                each_stock.sale_id = order_line.order_id.id
        if not stock_id:
            for each_categ in combo.get('combo_product'):
                if each_categ == 'required':
                    for each in combo.get('combo_product').get(each_categ):
                        product_id = self.env['product.product'].browse(each)
                        move_line_list.append((0, 0, {'name': 'Combo Product',
                                                      'product_uom': product_id.uom_id.id,
                                                      'product_categ': each_categ,
                                                      'is_required': True,
                                                      'product_id': each,
                                                      'product_uom_qty': 1,
                                                      }))
                else:
                    order_line_list = []
                    for each in combo.get('combo_product').get(each_categ):
                        product_id = self.env['product.product'].browse(each)
                        value.update({'location_id': product_id.property_stock_production.id})
                        move_line_list.append((0, 0, {'name': 'Combo Product',
                                                      'product_uom': product_id.uom_id.id,
                                                      'product_categ': each_categ,
                                                      'is_required': False,
                                                      'product_id': each,
                                                      'product_uom_qty': 1,
                                                      }))
            value.update({'combo_product_seq': combo.get('combo_sequence'),
                          'is_child': True,
                          'is_editable': True,
                          'scheduled_date': datetime.now(),
                          'partner_id': False,
                          'move_type': 'direct',
                          'picking_type_id': picking_type_id.id,
                          'sale_id': self.env['sale.order.line'].browse(combo.get('order_line')).order_id.id or False,
                          'priority': '1',
                          'location_dest_id': dest_location_id.id,
                          'location_id': picking_type_id.default_location_src_id.id,
                          'move_lines': move_line_list, })
            stock_picking_id = self.env['stock.picking'].create(value)
            if stock_picking_id:
                stock_picking_id.is_editable = True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
