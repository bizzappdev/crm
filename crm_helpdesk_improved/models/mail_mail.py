# -*- coding: utf-8 -*-
import base64
import logging
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv
from email.utils import parseaddr

_logger = logging.getLogger(__name__)


class mail_mail(osv.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _name = 'mail.mail'
    _inherit = 'mail.mail'

    def send_get_mail_subject(self, cr, uid, mail, force=False, partner=None, context=None):
        """ Add crm.helpdesk ticket id to subject

            :param boolean force: force the subject replacement
            :param browse_record mail: mail.mail browse_record
            :param browse_record partner: specific recipient partner
        """
        subject = super(mail_mail, self).send_get_mail_subject(cr, uid, mail, force, partner, context)
        if 'OVERDUE notification' in subject:
            pass
        elif mail.model == "crm.helpdesk":
            if mail.res_id:
                ticket_brw = self.pool.get("crm.helpdesk").browse(cr, uid, mail.res_id, context)
                subject = "%s [#%s]" % (ticket_brw.name, ticket_brw.ticket_id)
            else:
                if mail.record_name:
                    subject = mail.record_name
                else:
                    subject = self.pool.get("res.users").browse(cr, uid, uid, context).company_id.email
        return subject

    def send(self, cr, uid, ids, auto_commit=False, raise_exception=False, context=None):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        context = dict(context or {})
        ir_mail_server = self.pool.get('ir.mail_server')
        ir_attachment = self.pool['ir.attachment']
        for mail in self.browse(cr, SUPERUSER_ID, ids, context=context):
            try:
                # TDE note: remove me when model_id field is present on mail.message - done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model_id = self.pool['ir.model'].search(cr, SUPERUSER_ID, [('model', '=', mail.model)], context=context)[0]
                    model = self.pool['ir.model'].browse(cr, SUPERUSER_ID, model_id, context=context)
                else:
                    model = None
                if model:
                    context['model_name'] = model.name

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachment_ids = [a.id for a in mail.attachment_ids]
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                                 for a in ir_attachment.read(cr, SUPERUSER_ID, attachment_ids,
                                                             ['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, context=context))
                for partner in mail.recipient_ids:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, partner=partner, context=context))
                # headers
                headers = {}
                bounce_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.bounce.alias", context=context)
                catchall_domain = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.domain", context=context)
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s-%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s-%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({'state': 'exception'})
                mail_sent = False

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    if mail.model == 'crm.helpdesk':
                        email_cc = []
                        # Defaults
                        email_from = self.pool.get("res.users").browse(cr, uid, uid, context).company_id.companysupportmail or ''
                        reply_to = self.pool.get("res.users").browse(cr, uid, uid, context).company_id.email
                        # Proper department by ticket category
                        ticket_brw = self.pool.get(mail.model).browse(cr, uid, mail.res_id, context)
                        if ticket_brw.categ_id.email:
                            email_from = ticket_brw.categ_id.email
                            reply_to = ticket_brw.categ_id.email
                        # Email CC
                        # Look first if partner_id.email is in email_to (in order to avoid duplicates for cc -> only send to cc when sending to client)
                        for email_to in email.get('email_to'):
                            email_to_parsed = parseaddr(email_to)
                            if ticket_brw.partner_id.email == email_to_parsed[1]:  # Only Now we add cc
                                email_cc = [p.email for p in ticket_brw.email_cc_ids]
                        email_cc_2 = tools.email_split(mail.email_cc)
                        email_cc = email_cc + email_cc_2
                        #prevent mail circle to suppport email address
                        if email_from in email_cc:
                            email_cc.remove(email_from)
                    else:
                        email_support = self.pool.get("res.users").browse(cr, uid, uid, context).company_id.companysupportmail or ''
                        email_cc = tools.email_split(mail.email_cc)
                        email_from = mail.email_from
                        reply_to = self.pool.get("res.users").browse(cr, uid, uid, context).company_id.catchall
                        if email_support in email_cc:
                            email_cc.remove(email_support)

                    msg = ir_mail_server.build_email(
                        email_from=email_from,
                        email_to=email.get('email_to'),
                        subject=email.get('subject'),
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=email_cc,
                        reply_to=reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    try:
                        res = ir_mail_server.send_email(cr, uid, msg,
                                                    mail_server_id=mail.mail_server_id.id,
                                                    context=context)
                    except AssertionError as error:
                        if error.message == ir_mail_server.NO_VALID_RECIPIENT:
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.warning("Ignoring invalid recipients for mail.mail %s: %s",
                                            mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail.write({'state': 'sent', 'message_id': res})
                    mail_sent = True

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                if mail_sent:
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=mail_sent)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception('MemoryError while processing mail with ID %r and Msg-Id %r. '\
                                      'Consider raising the --limit-memory-hard startup option',
                                  mail.id, mail.message_id)
                raise
            except Exception as e:
                _logger.exception('failed sending mail.mail %s', mail.id)
                mail.write({'state': 'exception'})
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                cr.commit()
        return True
mail_mail()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
