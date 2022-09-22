# -*- coding: utf-8 -*-
{
    "name": "Odoo Integration",
    "version":"13.0",
    "category": "Sale",
    "depends": ['sale', 'stock', 'purchase', 'dxl_dawaai_extra_attributes', 'product_brand_inventory'],
    "data": [
        'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/partner_queue_view.xml',
        'views/product_queue_view.xml',
        'views/res_partner_view.xml',
        'views/product_category_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/brand_queue_view.xml',
    ],
    "installable": True,
    "application": True,
}
