# -*- coding: utf-8 -*-
import logging
from openerp import SUPERUSER_ID
from openerp.osv import osv

_logger = logging.getLogger(__name__)


class mail_message(osv.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    _name = 'mail.message'
    _inherit = 'mail.message'

    def _notify(self, cr, uid, newid, user_signature=None, force_send=False, context=None):
        """ Add the related record followers to the destination partner_ids if is not a private message.
            Call mail_notification.notify to manage the email sending
        """
        notification_obj = self.pool.get('mail.notification')
        message = self.browse(cr, uid, newid, context=context)

        partners_to_notify = set([])
        # message has no subtype_id: pure log message -> no partners, no one notified
        if not message.subtype_id:
            return True

        # all followers of the mail.message document have to be added as partners and notified
        if message.model and message.res_id:
            fol_obj = self.pool.get("mail.followers")
            # browse as SUPERUSER because rules could restrict the search results
            fol_ids = fol_obj.search(cr, SUPERUSER_ID, [
                ('res_model', '=', message.model),
                ('res_id', '=', message.res_id),
                ('subtype_ids', 'in', message.subtype_id.id)
                ], context=context)
            partners_to_notify |= set(fo.partner_id for fo in fol_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context))
        # remove me from notified partners, unless the message is written on my own wall
        if message.author_id and message.model == "res.partner" and message.res_id == message.author_id.id:
            partners_to_notify |= set([message.author_id])
        elif message.author_id:
            partners_to_notify -= set([message.author_id])

        # all partner_ids of the mail.message have to be notified regardless of the above (even the author if explicitly added!)
        if message.partner_ids:
            partners_to_notify |= set(message.partner_ids)

        # notify
        # CHANGED BY AGENT-ERP
        # CHANGED BY AGENT-ERP
        # CHANGED BY AGENT-ERP
        #if partners_to_notify:
        #    notification_obj._notify(cr, uid, newid, partners_to_notify=[p.id for p in partners_to_notify], context=context)
        notification_obj._notify(cr, uid, newid, partners_to_notify=[p.id for p in partners_to_notify], context=context)
        # CHANGED BY AGENT-ERP
        # CHANGED BY AGENT-ERP
        # CHANGED BY AGENT-ERP
        message.refresh()

        # An error appear when a user receive a notification without notifying
        # the parent message -> add a read notification for the parent
        if message.parent_id:
            # all notified_partner_ids of the mail.message have to be notified for the parented messages
            partners_to_parent_notify = set(message.notified_partner_ids).difference(message.parent_id.notified_partner_ids)
            for partner in partners_to_parent_notify:
                notification_obj.create(cr, uid, {
                    'message_id': message.parent_id.id,
                    'partner_id': partner.id,
                    'read': True,
                    }, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
