# -*- coding: utf-8 -*-
from openerp.osv import osv
import logging

_logger = logging.getLogger(__name__)


class mail_notification(osv.Model):
    _name = 'mail.notification'
    _inherit = 'mail.notification'

    def _notify(self, cr, uid, msg_id, context=None, force_send=False, partners_to_notify=None,user_signature=None):
        """ We override the _notify function in order to add the ticket partner to the partners_to_notify
            even if she is not a follower
        """
        if msg_id:
            msg_brw = self.pool.get('mail.message').browse(cr, uid, msg_id, context)
            if msg_brw.model == 'crm.helpdesk' and msg_brw.res_id and not context.get('dont_add_partner', False):
                ticket_brw = self.pool.get("crm.helpdesk").browse(cr, uid, msg_brw.res_id, context)
                partner_id = ticket_brw.partner_id and ticket_brw.partner_id.id or None
                if partner_id and partner_id not in partners_to_notify:
                    partners_to_notify.append(partner_id)
        return super(mail_notification, self)._notify(cr, uid, msg_id, partners_to_notify, context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
