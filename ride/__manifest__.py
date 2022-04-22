# -*- coding: utf-8 -*-
{
    'name': "ride",

    'summary': """
        Adds a data model for taxi rides""",

    'description': """
        Each record is a taxi ride
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Productivity',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],
    
    'assets': {
        'web.assets_backend': [
            'ride/static/src/css/ride_style.css',
        ],
    },

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/ride_views.xml',
        'views/ride_menu.xml',
        'views/ride_search.xml',
        'data/ride_sequence.xml',
        'data/bcv22_sequence.xml',
        'report/report.xml',
        'report/taxivoucherbatch.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application':True,
}
