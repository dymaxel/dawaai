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

from odoo import models, api


class SaleComboReport(models.AbstractModel):
    _name = 'report.aspl_sale_combo_ee.sale_combo_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = {}
        if not docids:
            docids = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        docs = self.env['sale.order'].browse(docids)
        for each_id in docids:
            for each_line in docs.order_line:
                if each_line.combo_product_sequence:
                    picking_ids = self.env['stock.picking'].search([('sale_id', '=', each_id), ('is_child', '=', True),
                                                                    ('combo_product_seq', '=', each_line.combo_product_sequence)])
                    combo_product = []
                    for each_product in picking_ids.move_lines:
                        combo_product.append(each_product.product_id.name)
                        data.update({each_line.product_id.id: {'product_name':each_line.product_id.name,
                                                               'combo_product': combo_product,
                                                               'quantity': each_line.product_uom_qty,
                                                               'unit_price': each_line.price_unit,
                                                               'sub_total': each_line.price_subtotal}})
                else:
                    data.update({each_line.product_id.id: {'product_name':each_line.product_id.name,
                                                           'quantity': each_line.product_uom_qty,
                                                           'unit_price': each_line.price_unit,
                                                           'sub_total': each_line.price_subtotal}})
        return {
            'data': data,
            'doc_model': 'sale.order',
            'docs': docs
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
