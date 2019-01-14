# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging
import uuid

_logger = logging.getLogger(__name__)


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        index = 0
        for arg in args:
            if arg[0] == 'dummy_partner_id':
                args[index] = ('id', arg[1], arg[2])
            index += 1
        return super(res_partner, self).search(cr, uid, args, offset, limit, order, context=context, count=count)

    def write(self, cr, uid, ids, vals, context=None):
        for partner_id in ids:
            vals.update({'dummy_partner_id': partner_id})
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def _get_cases_from_children(self, cr, uid, ids, field_names, arg=None, context=None):
        result = {}
        res = {}
        if not ids:
            return result
        for partner_id in ids:
            res[partner_id] = [partner_id]
            # get child partners
            child_partner_ids = self.search(cr, uid, [('parent_id', 'in', [partner_id])])
            res[partner_id] += child_partner_ids
            # get cases from all those contacts now
            case_ids = self.pool.get('crm.helpdesk').search(cr, uid, [('partner_id', 'in', res[partner_id])])
            result[partner_id] = case_ids or []
        return result

    _columns = {
        'dummy_partner_id': fields.many2one('res.partner', 'Partner', ),
        'case_ids': fields.one2many('crm.helpdesk', 'partner_id', 'Related Cases', ),
        'child_case_ids': fields.function(_get_cases_from_children, method=True, type='one2many', relation='crm.helpdesk', string='All company cases'),
        'unique_name': fields.char('Unique Name', size=64, ),
        }
    _sql_constraints = [
        ('unique_name_uniq', 'unique(unique_name)', 'Unique Name must be unique'),
    ]

    _defaults = {
        'opt_out': False,
        'notification_email_send': 'comment',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
