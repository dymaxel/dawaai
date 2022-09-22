# -*- coding: utf-8 -*-

from odoo import fields, models

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_auto_split = fields.Boolean(string="Is Auto Split", help="Allow to split picking when create planned transfer")

    def _get_action(self, action_xmlid):
        action = super(StockPickingType, self)._get_action(action_xmlid)
        context = action.get('context')
        if context and context.get('default_immediate_transfer'):
            context['default_immediate_transfer'] = False
        return action
