# -*- coding: utf-8 -*-
{
    "name": "CRM - Helpdesk - Improved",
    "version": "0.1",
    "author": "Agent-ERP",
    "category": 'Helpdesk and Support',
    'complexity': "easy",
    "description": """
CRM - Helpdesk - Improved
=========================================
Helpdesk System Improved

by Agent ERP
v0.1
    """,
    'website': 'http://www.agent-erp.de',
    "depends": [
        "mail",
        "sale",
        "crm",
        "crm_helpdesk",
        "crm_helpdesk_code",
    ],
    'init_xml': [],
    'data': [
        #'security/ir.model.access.csv',
        'security/security.xml',
        "data/emails.xml",
#        "data/crm_helpdesk_data.xml",
#        "data/crm_helpdesk_actions.xml",
         "views/crm_helpdesk_view.xml",
         "views/crm_helpdesk_category_view.xml",
#        "view/res_partner_view.xml",
         "views/crm_helpdesk_menu_view.xml",
#        "view/res_company_view.xml",
#        "view/mail_compose_message_view.xml",
#        "view/sale_view.xml",
#        "data/scheduler.xml",
#        "ir/cron.xml",
    ],
    'test': [],
    'application': False,
    'installable': True,
    'css': [
    ],
    'js': [
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
