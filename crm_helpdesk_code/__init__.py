# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import models
from odoo.api import Environment
from odoo import SUPERUSER_ID


new_field_code_added = False


def create_code_equal_to_id(cr):
    cr.execute("SELECT column_name FROM information_schema.columns "
               "WHERE table_name = 'crm_helpdesk' AND column_name = 'code'")
    if not cr.fetchone():
        cr.execute('ALTER TABLE crm_helpdesk '
                   'ADD COLUMN code character varying;')
        cr.execute('UPDATE crm_helpdesk '
                   'SET code = id;')
        global new_field_code_added
        new_field_code_added = True


def assign_old_sequences(cr, registry):
    if not new_field_code_added:
        # the field was already existing before the installation of the addon
        return
    with Environment.manage():
        env = Environment(cr, SUPERUSER_ID, {})

        sequence_model = env['ir.sequence']

        helpdesks = env['crm.helpdesk'].search([], order="id")
        for helpdesk in helpdesks:
            helpdesk.code = sequence_model.next_by_code('crm.helpdesk')
