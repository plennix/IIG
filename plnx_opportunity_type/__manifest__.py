{
    'name': 'Crm Opportunity Type',
    'version': '1.0',
    'description': 'Crm Opportunity Type',
    'summary': 'Crm Opportunity Type',
    'author': 'Plennix',
    'website': 'https://www.plennix.com',
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'depends': [
        'crm', 'sale', 'product', 'sale_crm'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/general_type.xml',
        'views/product_template_views.xml',
        'views/crm_stage.xml',
        'views/view.xml',
    ]
}