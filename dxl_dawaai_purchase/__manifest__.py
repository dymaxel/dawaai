# -*- coding: utf-8 -*-
{
    "name": "DXL Dawai Purchase",
    "version":"13.0",
    "category": "Purchase",
    "depends": ['purchase_stock', 'product_expiry'],
    "data": [
        'security/purchase_security.xml',
        'views/res_partner_view.xml',
        'views/product_view.xml',
        'views/stock_move_view.xml',
        'views/purchase_order_view.xml',
        'report/purchase_bill_report.xml',
        'report/stock_picking_report.xml',
        'wizard/stock_picking_return.xml',
    ],
    "installable": True,
    "application": True,
}
