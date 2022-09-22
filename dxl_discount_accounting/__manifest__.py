# -*- coding: utf-8 -*-
{
    'name': 'DXL Discount Accounting',
    'version': '13.0',
    'category': 'Accounting & Finance',
    'sequence': 1,
    'summary': 'Invoice Discount Entery',
    'description': """
Invoice Discount Entery
    """,
    'depends': ['account', 'sale', 'sale_margin'],
    'data': [
        'views/account_invoice_view.xml',
        'views/sale_order_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
