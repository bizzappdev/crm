# Copyright 2019 Agent ERP GmbH
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests import common


class TestCrmHelpdeskCode(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestCrmHelpdeskCode, cls).setUpClass()
        cls.crm_helpdesk_model = cls.env['crm.helpdesk']
        cls.ir_sequence_model = cls.env['ir.sequence']
        cls.crm_sequence = cls.env.ref('crm_helpdesk_code.sequence_helpdesk')
        cls.crm_helpdesk = cls.env['crm.helpdesk'].create({
            'name': 'Test Helpdesk',
        })

    def test_old_helpdesk_code_assign(self):
        crm_helpdesks = self.crm_helpdesk_model.search([])
        for crm_helpdesk in crm_helpdesks:
            self.assertNotEqual(crm_helpdesk.code, '/')

    def test_new_helpdesk_code_assign(self):
        code = self._get_next_code()
        crm_helpdesk = self.crm_helpdesk_model.create({
            'name': 'Testing helpdesk code',
        })
        self.assertNotEqual(crm_helpdesk.code, '/')
        self.assertEqual(crm_helpdesk.code, code)

    def test_copy_helpdesk_code_assign(self):
        code = self._get_next_code()
        crm_helpdesk_copy = self.crm_helpdesk.copy()
        self.assertNotEqual(crm_helpdesk_copy.code, self.crm_helpdesk.code)
        self.assertEqual(crm_helpdesk_copy.code, code)

    def _get_next_code(self):
        return self.crm_sequence.get_next_char(
            self.crm_sequence.number_next_actual
        )
