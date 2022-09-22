# -*- coding: utf-8 -*-

{
    'name': 'DXL Dawaai Sales Automation',
    'version': '13.0',
    'category': 'Sales Management',
    'description': """ DXL Dawaai Sales Automation """,
    'summary': 'DXL Dawaai Sales Automation',
    'depends': ['sale', 'stock_account', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_payment_view.xml',
    ],
    'installable': True,
    'application': True,
}
