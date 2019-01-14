# -*- coding: utf-8 -*-
from odoo import models
from odoo import fields
from odoo import osv


class CrmHelpdeskCategory(models.Model):

    _name = "crm.helpdesk.category"
    _description = "Category of Helpdesk Ticket"

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index', default=10)
    default_user_id = fields.Many2one('res.users', 'Default Responsible', required=True, )
    from_email = fields.Char('From Email', required=True,)
    default = fields.Boolean('Default Category')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
