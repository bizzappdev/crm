# Copyright 2019 Georg Notter <georg.notter@agenterp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class AccountAnalyticLineCase(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(AccountAnalyticLineCase, cls).setUpClass()
        Account = cls.env["account.analytic.account"]
        Project = cls.env["project.project"]
        cls.Line = cls.env["account.analytic.line"]
        cls.account1 = Account.create({
            "name": "Test Account 1",
        })
        cls.project1 = Project.create({
            "name": "Test Project 1",
            "analytic_account_id": cls.account1.id,
        })
        cls.lead = cls.env['crm.helpdesk'].create({
            'name': 'Test CRM Helpdesk Ticket',
            'project_id': cls.project1.id,
        })

    def test_onchange_lead(self):
        """Changing the lead changes the associated project."""
        line = self.Line.new({
            "crm_helpdesk_id": self.lead.id,
        })
        line._onchange_crm_helpdesk_id()
        self.assertEqual(line.project_id, self.project1)
