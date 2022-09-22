# -*- coding: utf-8 -*-
{
    'name': 'dxl_financial_dimensions',
    'description': 'dxl_financial_dimensions',
    'version': '13.0',
    'author': 'Warlock Technologies Pvt. Ltd.',
    'website': 'https://www.warlocktechnologies.com',
    'category': 'Custom',
    'depends': ['web', 'account_accountant', 'account', 'analytic', 'account_reports', 'purchase', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'views/assets.xml',
        'views/analytic_account_level_view.xml',
        'views/analytic_group_view.xml',
        'views/purchase_order_view.xml',
        'views/sale_order_view.xml',
        'views/res_user_view.xml',
    ],
    'installable': True,
    'application': True,
}
