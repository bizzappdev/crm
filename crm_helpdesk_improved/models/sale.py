# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class sale_order(osv.osv):

    _inherit = 'sale.order'

    _columns = {
        'crm_helpdesk_id': fields.many2one('crm.helpdesk', 'CRM Helpdesk', ),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
