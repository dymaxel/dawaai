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
{
    'name': 'Sales Order Combo (Enterprise)',
    'category': 'sale',
    'summary': 'This module allows user to use combo feature in sale order.',
    'description': """
This module allows user to use combo feature in sale order
""",
    'author': 'Acespritech Solutions Pvt. Ltd.',
    'website': 'http://www.acespritech.com',
    'price': 78,
    'currency': 'EUR',
    'version': '1.0.1',
    'depends': ['base', 'sale', 'stock', 'sale_management', 'purchase', 'mrp'],
    'images': ['static/description/main_screenshot.png'],
    "data": [
        'security/ir.model.access.csv',
        'views/sale_order.xml',
        'views/stock_picking_view.xml',
        'data/data.xml',
        'report/sale_combo_report.xml',
        'report/sale_combo_report_template.xml',
    ],
    'qweb': ['static/src/xml/sale_combo.xml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
