# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    current_mrp = fields.Float('Current Mrp')
    new_mrp = fields.Float('New Mrp')
    life_date = fields.Datetime(string='Expiry Date')
    pack_qty = fields.Float(string="Pack Qty")
    purchase_uom = fields.Many2one('uom.uom', compute='_compute_purchase_uom', string="Purchase UoM")

    @api.onchange('pack_qty')
    def _onchange_pack_qty(self):
        if self.pack_qty:
            self.qty_done = self.purchase_uom._compute_quantity(self.pack_qty, self.product_uom_id, rounding_method='HALF-UP')

    def _compute_purchase_uom(self):
        for line in self:
            if line.move_id.purchase_line_id:
                line.purchase_uom = line.move_id.purchase_line_id.product_uom.id
            elif line.move_id.picking_type_id.code == 'internal':
                line.purchase_uom = line.product_id.uom_po_id.id
            else:
                line.purchase_uom = False

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.lot_id:
            self.life_date = self.lot_id.life_date
            self.new_mrp = self.product_id.mrp

    @api.onchange('new_mrp')
    def _onchange_new_mrp(self):
        for line in self:
            move_line = self.env['stock.move.line'].search([('lot_id', '=', line.lot_id.id), ('state', '=', 'done')])
            if line.move_id.purchase_line_id and move_line and line.current_mrp != line.new_mrp and not self.env.user.has_group('dxl_dawaai_purchase.group_change_product_mrp'):
                raise ValidationError(_('You cannot update New Mrp on partial receipt.'))

    @api.onchange('life_date')
    def _onchange_life_date(self):
        for line in self:
            move_line = self.env['stock.move.line'].search([('lot_id', '=', line.lot_id.id), ('state', '=', 'done')])
            if line.move_id.purchase_line_id and move_line and line.life_date != move_line.lot_id.life_date:
                raise ValidationError(_('You cannot change expiry on same lot.'))

    @api.model
    def default_get(self, default_fields):
        vals = super(StockMoveLine, self).default_get(default_fields)
        if vals.get('move_id'):
            move = self.env['stock.move'].browse(vals.get('move_id'))
            if move.picking_type_id.code == 'incoming':
                vals['purchase_uom'] = move.purchase_line_id and move.purchase_line_id.product_uom.id or False
            if move.picking_type_id.code == 'internal':
                vals['purchase_uom'] = move.product_id.uom_po_id.id
        product = self.env['product.product'].browse(self._context.get('default_product_id'))
        if product:
            vals['current_mrp'] = product.mrp
            vals['new_mrp'] = product.mrp
        return vals

    @api.onchange('qty_done')
    def _onchange_qty_done(self):
        for line in self:
            if line.move_id.purchase_line_id and line.move_id.picking_type_id.code =='incoming' and line.qty_done > line.move_id.product_uom_qty:
                raise ValidationError(_('You cannot set done qty more than demand.')) 

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('lot_id') and not vals.get('life_date'):
                lot = self.env['stock.production.lot'].browse(vals.get('lot_id'))
                vals['life_date'] = lot and lot.life_date
        return super(StockMoveLine, self).create(vals_list)

class StockMove(models.Model):
    _inherit = 'stock.move'

    mrp_state = fields.Boolean(compute="compute_mrp_state")
    pack_qty = fields.Float(string="Demand Pack Qty")
    purchase_uom = fields.Many2one('uom.uom', related='product_id.uom_po_id', string="Purchase UoM")


    @api.onchange('pack_qty')
    def _onchange_pack_qty(self):
        if self.pack_qty:
            self.product_uom_qty = self.purchase_uom._compute_quantity(self.pack_qty, self.product_uom, rounding_method='HALF-UP')

    def compute_mrp_state(self):
        for move in self:
            if any(line.current_mrp != line.new_mrp for line in move.move_line_ids):
                move.mrp_state = True
            else:
                move.mrp_state = False

    def _action_done(self, cancel_backorder=False):
        for move in self:
            line_ids = move.move_line_ids.filtered(lambda x: x.lot_id and x.life_date)
            for line in line_ids:
                lot_line = line_ids.filtered(lambda x: x.lot_id.id == line.lot_id.id and line.id != x.id)
                if lot_line and ((lot_line.life_date != line.life_date) or (lot_line.new_mrp != line.new_mrp)):
                    raise ValidationError(_('Assigning of different expiry dates/mrp on same lot is not allowed.'))
                line.lot_id.write({'life_date': line.life_date, 'removal_date': line.life_date})
        return super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

    def _push_apply(self):
        for move in self:
            # if the move is already chained, there is no need to check push rules
            if move.move_dest_ids:
                continue
            # if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            # to receive goods without triggering the push rules again (which would duplicate chained operations)
            domain = [('location_src_id', '=', move.location_dest_id.id), ('action', 'in', ('push', 'pull_push'))]
            # first priority goes to the preferred routes defined on the move itself (e.g. coming from a SO line)
            warehouse_id = move.warehouse_id or move.picking_id.picking_type_id.warehouse_id
            if not self.env.context.get('force_company', False) and move.location_dest_id.company_id == self.env.user.company_id:
                rules = self.env['procurement.group']._search_rule(move.route_ids, move.product_id, warehouse_id, domain)
            else:
                rules = self.sudo().env['procurement.group']._search_rule(move.route_ids, move.product_id, warehouse_id, domain)

            # Filter stock rules to trigger only in GRN case.
            if move.picking_type_id.code != 'incoming':
                rules = rules.filtered(lambda x: not x.is_grn)

            # Make sure it is not returning the return
            if rules and (not move.origin_returned_move_id or move.origin_returned_move_id.location_dest_id.id != rules.location_id.id):
                rules._run_push(move)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    current_mrp = fields.Float('Current Mrp')
    new_mrp = fields.Float('New Mrp')

    @api.model
    def create(self, vals):
        product = self.env['product.product'].browse(vals['product_id'])
        if product and vals.get('lot_id'):
            ml = self.env['stock.move.line'].search([('lot_id', '=', vals.get('lot_id'))], limit=1)
            if ml:
                vals['current_mrp'] = ml.current_mrp
                vals['new_mrp'] = ml.new_mrp
        return super(StockQuant, self).create(vals)
