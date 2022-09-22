# -*- coding: utf-8 -*-

{
    'name': 'DXL Dawaai Extra Attribute',
    'version': '13.0',
    'category': 'product',
    'description': """ DXL Dawaai Product Extra Attribute """,
    'summary': 'DXL Dawaai Extra Attribute',
    'depends': ['sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_extra_attribute.xml',
        'views/product_template.xml',
    ],
    'installable': True,
    'application': True,
}
