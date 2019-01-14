# Copyright 2019 Georg Notter <georg.notter@agenterp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class CrmHelpdesk(models.Model):
    _inherit = 'crm.helpdesk'

    project_id = fields.Many2one(
        comodel_name='project.project',
        string="Project",
    )
    timesheet_ids = fields.One2many(
        comodel_name='account.analytic.line',
        inverse_name='crm_helpdesk_id',
        string="Timesheet",
    )