{
    'name': "CRM Helpdesk Timesheet",
    'category': 'Customer Relationship Management',
    'version': '11.0.1.0.0',
    'depends': [
        'crm_helpdesk',
        'hr_timesheet'
    ],
    'data': [
        'views/crm_helpdesk_view.xml',
        'views/hr_timesheet_view.xml'
    ],
    'author': 'Agent ERP GmbH'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/crm',
    'license': 'AGPL-3',
    'installable': True,
}
