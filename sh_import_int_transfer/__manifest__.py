# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name" : "Import Internal Transfer from CSV/Excel file",
    "author" : "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Warehouse",
    "summary": "This module useful to import internal transfer from csv/excel.",
    "description": """
    
 This module useful to import internal transfer from csv/excel. 

 
 

                    """,
    "version":"13.0.3",
    "depends" : ["base", "sh_message", "stock", "product"],
    "application" : True,
    "data" : [
        
            "security/import_int_transfer_security.xml",
            "wizard/import_int_transfer_wizard.xml",
            "views/stock_view.xml",
            
            ],
    "external_dependencies" : {
        "python" : ["xlrd"],
    },
    "images": ["static/description/background.png", ],
    "auto_install":False,
    "installable" : True,
    "price": 25,
    "currency": "EUR"   
}
