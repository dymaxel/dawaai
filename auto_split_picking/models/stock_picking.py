# -*- coding: utf-8 -*-
from odoo import fields, models

class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    src_loc_id = fields.Many2one('stock.location', string='Origin Location')
    dest_loc_id = fields.Many2one('stock.location', string='Destination Location')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    src_loc_id = fields.Many2one('stock.location', related='group_id.src_loc_id', string='Origin Location')
    dest_loc_id = fields.Many2one('stock.location', related='group_id.dest_loc_id', string='Destination Location')

    def action_confirm(self):
        for picking in self:
            if picking.picking_type_id.is_auto_split and not picking.group_id:
                group_id = self.env["procurement.group"].create({'name': picking.name, 'src_loc_id': picking.location_id.id, 'dest_loc_id': picking.location_dest_id.id})
                todo = picking.move_lines.write({'group_id': group_id.id})
            if picking.picking_type_id.is_auto_split and picking.group_id:
                picking.group_id.write({'src_loc_id': picking.location_id.id, 'dest_loc_id': picking.location_dest_id.id})
        return super(StockPicking, self).action_confirm()

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if 'note' in vals and self.picking_type_id.is_auto_split and self.group_id:
            dest_pickings = self.search([('group_id', '=', self.group_id.id)]) - self
            if self.note not in dest_pickings.mapped('note'):
                dest_pickings.write({'note': self.note})
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_move_dest_ids(self, final_moves=None):
        dest_moves = self.env['stock.move']
        final_moves = final_moves or self.env['stock.move']
        for move in self:
            if move.move_dest_ids:
                dest_moves |= move.move_dest_ids
            else:
                final_moves |= move
        if dest_moves:
            final_moves |= dest_moves._get_move_dest_records(final_moves)
        return final_moves
