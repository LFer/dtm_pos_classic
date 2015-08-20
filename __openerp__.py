{
    'name': 'Point Of Sale - Classic UI :)',
    'version': '1.0',
    'depends': ['base', 'dtm_multi_store', 'point_of_sale'],
    'author': 'Alexia Rodriguez',
    'website': 'http://www.datamatic.com.uy',
    'category': 'Datamatic',
    'summary': 'Classic UI for the Point Of Sale',
    'description': """
    Point Of Sale with a classic UI
    """,
    'data': [
        'views/point_of_sale_view.xml',
        'data/partner_data.xml',
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',

    ],
    'demo': [
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
