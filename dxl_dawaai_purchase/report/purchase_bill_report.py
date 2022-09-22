# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from functools import partial

import psycopg2
import pytz

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
from odoo.osv.expression import AND
import base64

_logger = logging.getLogger(__name__)


class ReportPurchaseBill(models.AbstractModel):
    _name = 'report.dxl_dawaai_purchase.report_purchasebill'
    _description = 'Purchase Draft Bill'

    def _get_report_name(self):
        return self.env['purchase.order'].browse(self.id).name

    def _prepare_picking_quantity(self, purchase_id):
        data = {}
        moves = self.env['stock.move'].search([('purchase_line_id', 'in', purchase_id.order_line.ids)])
        for line in purchase_id.order_line:
            product_uom = moves.mapped('product_uom')
            done_qty = sum(moves.filtered(lambda x: x.purchase_line_id.id == line.id and x.state != 'done').mapped('quantity_done'))
            data[line.id] = product_uom._compute_quantity(done_qty, line.product_uom, rounding_method='HALF-UP')
        return data

    def _get_subtotal(self, purchase_id, po_data):
        sub_total = tax_total = final_total = 0.0
        for line in purchase_id.order_line:
            taxes = line.taxes_id.compute_all(line.price_unit, line.currency_id, po_data[line.id], line.product_id, line.partner_id)
            sub_total += taxes['total_excluded']
            tax_total += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            final_total += taxes['total_included']
        return sub_total, tax_total, final_total

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_id = self.env['purchase.order'].browse(docids)
        po_data = self._prepare_picking_quantity(purchase_id)
        sub_total, tax_total, final_total = self._get_subtotal(purchase_id, po_data)
        data.update({
            'purchase_id': purchase_id,
            'receive_line_qty': po_data,
            'tax_total': tax_total,
            'sub_total': sub_total,
            'final_total': final_total,
        })
        return data
