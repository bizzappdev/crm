from odoo import api, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'crm.helpdesk' and self._context.get('default_res_id'):
            ticket = self.env['crm.helpdesk'].browse([self._context['default_res_id']])
            ticket.with_context(tracking_disable=True).state = self._context.get('default_next_state')
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
