# -*- coding: utf-8 -*-

{
    'name': 'DXL Accounting Force Date',
    'version': '13.0',
    'category': 'Accounting',
    'description': """ DXL accounting force date""",
    'summary': 'DXL accounting force date',
    'depends': ['sale_management', 'stock_account'],
    'data': [
        'views/sale_order_view.xml',
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'application': True,
}
