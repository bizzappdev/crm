# -*- coding: utf-8 -*-
from odoo import api
from odoo import _
from odoo import fields
from odoo import models
from odoo import exceptions
from email.utils import parseaddr
import time
import logging
from odoo import SUPERUSER_ID

_logger = logging.getLogger(__name__)

class CrmHelpdesk(models.Model):
    _inherit = "crm.helpdesk"
    _order = "create_date DESC"

    state = fields.Selection(
        [('draft', 'New'),
            ('pending', 'In Progress'),
            ('todeploy', 'To Deploy'),
            ('pending_client', 'Waiting client'),
            ('pending_external', 'Waiting third party'),
            ('feedback', 'Waiting Feedback'),
            ('done', 'Closed'),
            ],
        'Status',
        size=64,
        readonly=True,
        track_visibility='onchange',
        help='The status is set to \'Draft\', when a ticket is created.\
            \nIf the ticket is in progress the status is set to \'Open\'.\
            \nWhen the ticket is over, the status is set to \'Done\'.\
            \nIf the ticket needs to be reviewed then the status is set to \'Pending\'.')
    date_overdue_notification = fields.Date('Overdue notification', readonly=True, help="Stores the date of the last notification on over")
    solution = fields.Text('Solution')

    #related_helpdesk_ids = fields.Many2many('crm.helpdesk', 'crm_helpdesk_crm_helpdesk_rel', 'orig_id', 'dest_id', 'Related Tickets', )
    #related_task_ids = fields.Many2many('project.task', 'crm_helpdesk_project_task_rel', 'orig_id', 'dest_id', 'Related Tasks', )
    #related_saleorder_ids = fields.One2many('sale.order', 'crm_helpdesk_id', 'Related Sale Order', )
    #categ_name = fields.related('categ_id', 'name', type='char', readonly=True, relation='crm_case_categ', string='Categ Name')
    #categ_id = fields.related('categ_id', 'name', type='char', readonly=True, relation='crm_case_categ', string='Categ Name'), default llala

    @api.model
    def notify_overdue(self):
        domain = [
            '&',
            ('state', 'not in', ['done', 'cancel']),
            '&',
            ('date_deadline', '<=', fields.date.context_today(self, cr, uid, context=context)),
            ('date_overdue_notification', '=', False)
        ]
        ticket_ids = self.search(domain)
        for rec in ticket_ids:
            template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_overdue', False)
            mail = template.send_mail(
                res_id=rec.id,
                force_send=False,
            )
            if mail:
                rec.write({
                    'date_overdue_notification':
                    fields.date.context_today(context=context)
                })

    @api.model
    def clean_overdue_messages(self):
        domain = [
            '&',
            ('model', '=', 'crm.helpdesk'),
            ('subject', 'like', 'OVERDUE notification'),
        ]
        message_ids = self.env['mail.message'].search(domain)
        if message_ids:
            message_ids.unlink()

    @api.multi
    def create_partner_if_not_exists(self):
        for rec in self:
            if not rec.partner_id and rec.email_from:
                parts = parseaddr(ticket_brw.email_from)
                name = parts[0] or parts[1]
                email = parts[1]
                # First we check that the email doesn's exists
                partner_ids = self.pool.get("res.partner").search(cr, uid, [('email', '=', email)], limit=1)
                if not partner_ids:
                    vals = {    'name':     name,
                                'email':    email,
                                'customer': True,
                                'is_company': False,
                                }
                    partner_id = self.pool.get("res.partner").create(cr, uid, vals, context)
                    self.write(cr, uid, [ticket_brw.id], {'partner_id': partner_id}, context)
        return True

    @api.multi
    def notify_responsible_on_creation(self):
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_responsible', False)
        for rec in self:
            mail = template.send_mail(
                res_id=rec.id,
                force_send=False,
            )

    @api.multi
    def copy(self, default=None):
        data = self.copy_data(default)
        # We remove messages from original ticket
        data.update({'message_ids': None})
        # Get new ticket_id
        old_ticket_id = data['ticket_id']
        data['ticket_id'] = int(self.pool.get('ir.sequence').get(cr, uid, 'crm.helpdesk'))
        data['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        new_id = self.create(data)
        self.copy_translations(cr, uid, ticket_id, new_id, context)
        # Add copy quote linked to Messages
        link = "<a href='/?db=%s#id=%s&view_type=form&model=crm.helpdesk&menu_id=183&action=179'>%s</a>" % (cr.dbname, old_ticket_id, old_ticket_id, )
        message = "Duplicated ticket from: %s\n\n%s" % (link, data['description'])
        self.message_post(cr, uid, new_id, body=message, context=context)
        return new_id

    @api.model
    def send_welcome(self):
        categ_id = self.env[('crm.case.categ')].search([('default','=',True)])
        for rec in self.search([('categ_id','=',categ_id.id),('state','=','draft')]):
            rec.write({'state' : 'open'})
            template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_oncreate')
            template.send_mail(rec.id, force_send=True)
        return True

    @api.multi
    def write(self, vals):
        result = super(CrmHelpdesk, self).write(vals)
        return result

    @api.multi
    def _get_default_categ(self):
        return self.env['crm.case.categ'].sudo().search([('default','=',True)], limit=1)

    def _get_project_id(self):
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id
        else:
            partner_id = self.partner_id
        project_id = self.env['project.project'].search([('partner_id','=',partner_id)])
        return project_id.id

    @api.multi
    def case_progress(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_progress', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='pending',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_close(self):
        self.ensure_one()
        if not self.solution:
            raise exceptions.ValidationError('You need to specifiy a solution.')
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_close', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='done',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_reopen(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_reopen', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='draft',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_pending(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_pending', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='pending',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_todeploy(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_todeploy', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='todeploy',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_pending_external(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_pexternal', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='pending_external',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_pending_kunde(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_pendingcustomer', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='pending_client',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def case_feedback(self):
        self.ensure_one()
        template = self.env.ref('crm_helpdesk_improved.crm_helpdesk_notify_customer_feedback', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.helpdesk',
            default_res_id=self.id,
            default_next_state='feedback',
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def billed_task(self):
        project_task_pool = self.env['project.task']
        project_tasktype_pool = self.env['project.task.type']
        task_done_id = project_tasktype_pool.search([('name','=','Erledigt')])
        project_task_work_pool = self.env['project.task.work']
        project_ids = self.env['project.project'].search([('partner_id','=',self.partner_id.parent_id and self.partner_id.parent_id.id or self.partner_id.id)])
        res = {
            'name' : self.name or '',
            'stage_id' : task_done_id.id,
            'user_id' : self._uid,
            'project_id' : project_ids and project_ids[0] and project_ids[0].id or False,
            'planned_hours' : self.task_invoice_time,
        }
        tid = project_task_pool.create(res)
        wres= {
            'name': self.name + ' Ticket: #' + self.ticket_id or '',
            'hours' : self.task_invoice_time,
            'user_id' : self._uid,
            'task_id': tid.id
        }
        wid = project_task_work_pool.create(wres)
        test = self.write({'related_task_ids': [(4, tid.id)]})
        return True

    @api.multi
    def open_task(self):
        project_task_pool = self.env['project.task']
        project_tasktype_pool = self.env['project.task.type']
        task_done_id = project_tasktype_pool.search([('name','=','New')])
        project_task_work_pool = self.env['project.task.work']
        project_ids = self.env['project.project'].search([('partner_id','=',self.partner_id.parent_id and self.partner_id.parent_id.id or self.partner_id.id)])
        res = {
            'name': self.name + ' Ticket: #' + self.ticket_id or '',
            'stage_id' : self.task_state_id.id,
            'planned_hours' : self.task_invoice_time,
            'date_deadline' : self.date_deadline,
            'reviewer_id' : self._uid,
            'user_id' : self.task_user_id.id,
            'project_id' : self.task_project_id and self.task_project_id.id or project_ids and project_ids[0] and project_ids[0].id or False,
        }
        tid = project_task_pool.create(res)
        tid.message_post(self.description,'Beschreibung der Aufgabe:')
        wres= {
            'name': self.name + ' Ticket: #' + self.ticket_id or '',
            'hours' : self.task_invoice_time,
            'user_id' : self._uid,
            'task_id': tid.id
        }
        wid = project_task_work_pool.create(wres)
        attachments = self.env['ir.attachment'].search([('res_model','=','crm.helpdesk'),('res_id','=',self.id)])
        for att in attachments:
            att.copy(default={'res_id': tid.id, 'res_model': 'project.task'})
        self.write({'related_task_ids': [(4, tid.id)]})
        return True
