# -*- coding: utf-8 -*-
{
    'name': 'DXL Partner Smart GL',
    'version': '13.0',
    'category': 'Accounting',
    'summary': 'Show General Ledger on partner',
    'depends': ['account_reports'],
    'data': [
        'views/account_account_view.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
