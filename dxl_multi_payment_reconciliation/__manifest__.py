# -*- coding: utf-8 -*-
{
    "name": "DXL Multi Payment Reconciliation",
    "version":"13.0",
    "category": "Account",
    "depends": ['account', 'tds_withholding_tax_cv'],
    'data': [
    	'security/ir.model.access.csv',
    	'views/account_payment_view.xml',
        'report/report_action.xml',
    ],
    "installable": True,
    "application": True,
}
