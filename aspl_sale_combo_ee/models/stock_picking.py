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

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    combo_product_seq = fields.Char(string='Combo Product')
    is_child = fields.Boolean(string='Child Picking(Combo)')
    is_editable = fields.Boolean(string='Editable')


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_categ = fields.Char( string='Product Category')
    is_required = fields.Boolean(string='Required')


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        pick_to_backorder = self.env['stock.picking']
        pick_to_do = self.env['stock.picking']
        for picking in self.pick_ids:
            move_id = self.env['stock.move'].search([('picking_id', '=', picking.id)])
            if picking.is_child:
                # If still in draft => confirm and assign
                if picking.state == 'draft':
                    picking.action_confirm()
                    if picking.state != 'assigned':
                        picking.action_assign()
                        if picking.state != 'assigned':
                            raise UserError(_(
            # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
                    "Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
                for move in picking.move_lines:
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
                if picking._check_backorder():
                    pick_to_backorder |= picking
                    continue
                pick_to_do |= picking
            # Process every picking that do not require a backorder, then return a single backorder wizard for every other ones.
                if pick_to_do:
                    todo_moves = picking.mapped('move_lines').filtered(
                        lambda self: picking.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
                    # Check if there are ops not linked to moves yet
                    for pick in picking:
                        for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                            # Search move with this product
                            moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
                            moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
                            if moves:
                                ops.move_id = moves[0].id
                            else:
                                new_move = self.env['stock.move'].create({
                                    'name': _('New Move:') + ops.product_id.display_name,
                                    'product_id': ops.product_id.id,
                                    'product_uom_qty': ops.qty_done,
                                    'product_uom': ops.product_uom_id.id,
                                    'location_id': pick.location_id.id,
                                    'location_dest_id': pick.location_dest_id.id,
                                    'picking_id': pick.id,
                                    'picking_type_id': pick.picking_type_id.id,
                                })
                                ops.move_id = new_move.id
                                new_move._action_confirm()
                                todo_moves |= new_move
                                # 'qty_done': ops.qty_done})
                    # todo_moves._action_done()
                    move_id.product_price_update_before_done()
                    for each_move in move_id:
                        if each_move._is_in() and each_move._is_out():
                            raise UserError(_(
                                "The move lines are not in a consistent state: some are entering and other are leaving the company."))
                        company_src = each_move.mapped('move_line_ids.location_id.company_id')
                        company_dst = each_move.mapped('move_line_ids.location_dest_id.company_id')
                        try:
                            if company_src:
                                company_src.ensure_one()
                            if company_dst:
                                company_dst.ensure_one()
                        except ValueError:
                            raise UserError(_(
                                "The move lines are not in a consistent states: they do not share the same origin or destination company."))
                        if company_src and company_dst and company_src.id != company_dst.id:
                            raise UserError(_(
                                "The move lines are not in a consistent states: they are doing an intercompany in a single step while they should go through the intercompany transit location."))
                        # if each_move._is_in():
                        #     each_move._create_in_svl()
                        # if each_move._is_out():
                        #     each_move._create_out_svl()
                        each_move.write({'state': 'done'})
                    picking.write({'date_done': fields.Datetime.now()})
                if pick_to_backorder:
                    return pick_to_backorder.action_generate_backorder_wizard()
            if not picking.is_child:
                return super(StockImmediateTransfer, self).process()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
