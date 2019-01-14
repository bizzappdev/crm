# -*- coding: utf-8 -*-
from openerp.osv import osv
import logging

_logger = logging.getLogger(__name__)


class mail_compose_message(osv.TransientModel):
    _inherit = 'mail.compose.message'

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        res = super(mail_compose_message, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        user_brw = self.pool.get("res.users").browse(cr, uid, uid, context)
        isAdmin = False
        for group_brw in user_brw.groups_id:
            isAdmin = isAdmin or 'CRM Helpdesk Admin' == group_brw.name
        if not isAdmin:
            res['arch'] = res['arch'].replace("<button icon=\"/email_template/static/src/img/email_template_save.png\" type=\"object\" name=\"save_as_template\" string=\"Save as new template\" class=\"oe_link\" help=\"Save as a new template\"/>", "")
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
