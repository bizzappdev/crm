# Copyright 2019 Georg Notter <georg.notter@agenterp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    crm_helpdesk_id = fields.Many2one(
        comodel_name='crm.helpdesk',
        string='Crm Helpdesk',
    )

    @api.onchange('crm_helpdesk_id')
    def _onchange_crm_helpdesk_id(self):
        if self.crm_helpdesk_id.project_id:
            self.project_id = self.crm_helpdesk_id.project_id.id
