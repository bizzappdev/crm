# Copyright 2019 Agent ERP GmbH
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Sequential Code for CRM Helpdesk",
    "version": "11.0.1.0.0",
    "category": "Customer Relationship Management",
    "author":
              "Agent ERP GmbH, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/crm",
    "license": "LGPL-3",
    "depends": [
        "crm_helpdesk",
    ],
    "data": [
        "views/crm_helpdesk_view.xml",
        "data/sequence.xml",
    ],
    'installable': True,
}
