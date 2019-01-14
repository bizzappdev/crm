# Copyright 2019 Agent ERP GmbH
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class CrmHelpdesk(models.Model):
    _inherit = "crm.helpdesk"

    code = fields.Char(
        string='Ticket Number',
        required=True,
        default="/",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        ('crm_helpdesk_unique_code', 'UNIQUE (code)',
         'The code must be unique!'),
    ]

    @api.model
    def create(self, values):
        if values.get('code', '/') == '/':
            values['code'] = self.env['ir.sequence'].next_by_code('crm.helpdesk')
        return super(CrmHelpdesk, self).create(values)
