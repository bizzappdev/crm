# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import base64
from collections import OrderedDict
import datetime
import dateutil
import email
try:
    import simplejson as json
except ImportError:
    import json
from lxml import etree
import logging
import pytz
import re
import socket
import time
import xmlrpclib
from email.message import Message
from email.utils import formataddr
from urllib import urlencode

from openerp import api, tools
from openerp import SUPERUSER_ID
from openerp.addons.mail.mail_message import decode
from openerp.osv import fields, osv, orm
from openerp.osv.orm import BaseModel
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from email.utils import parseaddr

_logger = logging.getLogger(__name__)


mail_header_msgid_re = re.compile('<[^<>]+>')

def decode_header(message, header, separator=' '):
    return separator.join(map(decode, filter(None, message.get_all(header, []))))


class mail_thread(osv.AbstractModel):
    ''' mail_thread model is meant to be inherited by any model that needs to
        act as a discussion topic on which messages can be attached. Public
        methods are prefixed with ``message_`` in order to avoid name
        collisions with methods of the models that will inherit from this class.

        ``mail.thread`` defines fields used to handle and display the
        communication history. ``mail.thread`` also manages followers of
        inheriting classes. All features and expected behavior are managed
        by mail.thread. Widgets has been designed for the 7.0 and following
        versions of OpenERP.

        Inheriting classes are not required to implement any method, as the
        default implementation will work for any model. However it is common
        to override at least the ``message_new`` and ``message_update``
        methods (calling ``super``) to add model-specific behavior at
        creation and update of a thread when processing incoming emails.

        Options:
            - _mail_flat_thread: if set to True, all messages without parent_id
                are automatically attached to the first message posted on the
                ressource. If set to False, the display of Chatter is done using
                threads, and no parent_id is automatically set.
    '''
    _inherit = 'mail.thread'

    def message_route(self, cr, uid, message, message_dict, model=None, thread_id=None,
                      custom_values=None, context=None):
        """Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail.aliases, for example.

        The following heuristics are used, in this order:
             1. If the message replies to an existing thread_id, and
                properly contains the thread model in the 'In-Reply-To'
                header, use this model/thread_id pair, and ignore
                custom_value (not needed as no creation will take place)
             2. Look for a mail.alias entry matching the message
                recipient, and use the corresponding model, thread_id,
                custom_values and user_id.
             3. Fallback to the ``model``, ``thread_id`` and ``custom_values``
                provided.
             4. If all the above fails, raise an exception.

           :param string message: an email.message instance
           :param dict message_dict: dictionary holding message variables
           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :type dict custom_values: optional dictionary of default field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. Only used if the message
               does not reply to an existing thread and does not match any mail alias.
           :return: list of [model, thread_id, custom_values, user_id, alias]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        mail_msg_obj = self.pool['mail.message']
        fallback_model = model

        # Get email.message.Message variables for future processing
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')
        references = decode_header(message, 'References')
        in_reply_to = decode_header(message, 'In-Reply-To')
        subject = decode_header(message, 'Subject')
        thread_references = references or in_reply_to

        # 0. Check to Which case it it matches!
        if subject:
            ticket_id = ''
            route_obj = []
            p = re.compile('\[#\d+\]')
            print "matching ", p.findall(subject)
            ticket_tokens = p.findall(subject)
            for ticket_token in ticket_tokens:
                _logger.info('mail with subject %s has the following ticket tocken %s', subject, ticket_token)
                ticket_id = ticket_token.replace('[#','').replace(']','')
                if ticket_id:
                    ticket_ids = self.pool.get('crm.helpdesk').search(cr, uid, [('ticket_id', '=', ticket_id)], limit=1, context=context)
                    if ticket_ids:
                        ticket = self.pool.get('crm.helpdesk').browse(cr, uid, ticket_ids[0], context=context)
                        ticket.write({'state' : 'open'})
                        _logger.info('Routing mail from %s to %s with Message-Id %s: Into Case %s, , custom_values: %s, uid: %s',
                                        email_from, email_to, message_id, ticket.id, custom_values, uid)
                route = self.message_route_verify(
                            cr, uid, message, message_dict,
                            ('crm.helpdesk', ticket.id, custom_values, uid, None),
                            update_author=True, assert_model=True, create_fallback=True, context=context)
                route_obj.append(route)
            if route_obj:
                return route_obj


        # 1. message is a reply to an existing message (exact match of message_id)
        ref_match = thread_references and tools.reference_re.search(thread_references)
        msg_references = mail_header_msgid_re.findall(thread_references)
        mail_message_ids = mail_msg_obj.search(cr, uid, [('message_id', 'in', msg_references)], context=context)
        if ref_match and mail_message_ids:
            original_msg = mail_msg_obj.browse(cr, SUPERUSER_ID, mail_message_ids[0], context=context)
            model, thread_id = original_msg.model, original_msg.res_id
            route = self.message_route_verify(
                cr, uid, message, message_dict,
                (model, thread_id, custom_values, uid, None),
                update_author=True, assert_model=False, create_fallback=True, context=context)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, uid)
                return [route]

        # 2. message is a reply to an existign thread (6.1 compatibility)
        if ref_match:
            reply_thread_id = int(ref_match.group(1))
            reply_model = ref_match.group(2) or fallback_model
            reply_hostname = ref_match.group(3)
            local_hostname = socket.gethostname()
            # do not match forwarded emails from another OpenERP system (thread_id collision!)
            if local_hostname == reply_hostname:
                thread_id, model = reply_thread_id, reply_model
                if thread_id and model in self.pool:
                    model_obj = self.pool[model]
                    compat_mail_msg_ids = mail_msg_obj.search(
                        cr, uid, [
                            ('message_id', '=', False),
                            ('model', '=', model),
                            ('res_id', '=', thread_id),
                        ], context=context)
                    if compat_mail_msg_ids and model_obj.exists(cr, uid, thread_id) and hasattr(model_obj, 'message_update'):
                        route = self.message_route_verify(
                            cr, uid, message, message_dict,
                            (model, thread_id, custom_values, uid, None),
                            update_author=True, assert_model=True, create_fallback=True, context=context)
                        if route:
                            _logger.info(
                                'Routing mail from %s to %s with Message-Id %s: direct thread reply (compat-mode) to model: %s, thread_id: %s, custom_values: %s, uid: %s',
                                email_from, email_to, message_id, model, thread_id, custom_values, uid)
                            return [route]

        # 3. Reply to a private message
        if in_reply_to:
            mail_message_ids = mail_msg_obj.search(cr, uid, [
                                ('message_id', '=', in_reply_to),
                                '!', ('message_id', 'ilike', 'reply_to')
                            ], limit=1, context=context)
            if mail_message_ids:
                mail_message = mail_msg_obj.browse(cr, uid, mail_message_ids[0], context=context)
                route = self.message_route_verify(cr, uid, message, message_dict,
                                (mail_message.model, mail_message.res_id, custom_values, uid, None),
                                update_author=True, assert_model=True, create_fallback=True, allow_private=True, context=context)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: direct reply to a private message: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, mail_message.id, custom_values, uid)
                    return [route]

        # 4. Look for a matching mail.alias entry
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = \
             ','.join([decode_header(message, 'Delivered-To'),
                       decode_header(message, 'To'),
                       decode_header(message, 'Cc'),
                       decode_header(message, 'Resent-To'),
                       decode_header(message, 'Resent-Cc')])
        local_parts = [e.split('@')[0] for e in tools.email_split(rcpt_tos)]
        if local_parts and 'support' not in local_parts:
            mail_alias = self.pool.get('mail.alias')
            alias_ids = mail_alias.search(cr, uid, [('alias_name', 'in', local_parts)])
            if alias_ids:
                routes = []
                for alias in mail_alias.browse(cr, uid, alias_ids, context=context):
                    user_id = alias.alias_user_id.id
                    if not user_id:
                        # TDE note: this could cause crashes, because no clue that the user
                        # that send the email has the right to create or modify a new document
                        # Fallback on user_id = uid
                        # Note: recognized partners will be added as followers anyway
                        # user_id = self._message_find_user_id(cr, uid, message, context=context)
                        user_id = uid
                        _logger.info('No matching user_id for the alias %s', alias.alias_name)
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, eval(alias.alias_defaults), user_id, alias)
                    route = self.message_route_verify(cr, uid, message, message_dict, route,
                                update_author=True, assert_model=True, create_fallback=True, context=context)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 5. Fallback to the provided parameters, if they work
        if not thread_id:
            # Legacy: fallback to matching [ID] in the Subject
            match = tools.res_re.search(decode_header(message, 'Subject'))
            thread_id = match and match.group(1)
            # Convert into int (bug spotted in 7.0 because of str)
            try:
                thread_id = int(thread_id)
            except:
                thread_id = False
        route = self.message_route_verify(cr, uid, message, message_dict,
                        (fallback_model, thread_id, custom_values, uid, None),
                        update_author=True, assert_model=True, context=context)
        if route:
            _logger.info(
                'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                email_from, email_to, message_id, fallback_model, thread_id, custom_values, uid)
            return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
                'No possible route found for incoming message from %s to %s (Message-Id %s:). '
                'Create an appropriate mail.alias or force the destination model.' %
                (email_from, email_to, message_id)
            )

    def message_process(self, cr, uid, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None, context=None):
        """ Process an incoming RFC2822 email message, relying on
            ``mail.message.parse()`` for the parsing operation,
            and ``message_route()`` to figure out the target model.

            Once the target model is known, its ``message_new`` method
            is called with the new message (if the thread record did not exist)
            or its ``message_update`` method (if it did).

            There is a special case where the target model is False: a reply
            to a private message. In this case, we skip the message_new /
            message_update step, to just post a new message using mail_thread
            message_post.

           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :param message: source of the RFC2822 message
           :type message: string or xmlrpclib.Binary
           :type dict custom_values: optional dictionary of field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param bool save_original: whether to keep a copy of the original
                email source attached to the message after it is imported.
           :param bool strip_attachments: whether to strip all attachments
                before processing the message, in order to save some space.
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. When provided, this
               overrides the automatic detection based on the message
               headers.
        """
        if context is None:
            context = {}

        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg = self.message_parse(cr, uid, msg_txt, save_original=save_original, context=context)
        if strip_attachments:
            msg.pop('attachments', None)
        cc = msg['cc'] and msg['cc'].split(',') or None
        if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            existing_msg_ids = self.pool.get('mail.message').search(cr, SUPERUSER_ID, [
                                                                ('message_id', '=', msg.get('message_id')),
                                                                ], context=context)
            if existing_msg_ids:
                _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                                msg.get('from'), msg.get('to'), msg.get('message_id'))
                return False

    	# find possible routes for the message
        routes = self.message_route(cr, uid, msg_txt, msg, model, thread_id, custom_values, context=context)
        thread_id = self.message_route_process(cr, uid, msg_txt, msg, routes, context=context)
	if cc:
            ticket_brw = self.pool.get('crm.helpdesk').browse(cr, uid, thread_id, context)
            # We add current ccs
            current_cc = [p.email for p in ticket_brw.email_cc_ids]
            # We add partner itself, we dont want it in cc followers
            if ticket_brw and ticket_brw.partner_id:
                current_cc += ticket_brw.partner_id.email
            current_cc_ids = self.pool.get('res.partner').search(cr, uid, [('email', 'in', current_cc)])
            for cc_item in cc:
                parsed_cc = parseaddr(cc_item)
                if not parsed_cc[1] in current_cc:
                    # Look is partner already exists in system
                    domain = [('email', '=', parsed_cc[1])]
                    partner_ids = self.pool.get('res.partner').search(cr, uid, domain)
                    # Create new partner if needed
                    if not partner_ids:
                        vals = {
                            'is_company': False,
                            'name': parsed_cc[0] or parsed_cc[1],
                            'email': parsed_cc[1],
                        }
                        partner_id = self.pool.get('res.partner').create(cr, uid, vals, context)
                        partner_ids = [partner_id]
                    # Update Ticket cc's
                    if partner_ids:
                        values = {'email_cc_ids': [(6, 0, partner_ids + current_cc_ids)]}  # Avoid duplicates
                        self.pool.get('crm.helpdesk').write(cr, uid, [thread_id], values, context)
                    else:
                        _logger.error("Something went wrong trying to add parsed_cc[1] = %s" % (parsed_cc[1], ))


        return thread_id


