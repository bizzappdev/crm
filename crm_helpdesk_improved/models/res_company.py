# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class res_company(osv.osv):
    _name = "res.company"
    _inherit = "res.company"

    _columns = {
        'default_imacs_user_id': fields.many2one('res.users', 'Default IMACS Responsible', select=True),
        'catchall': fields.char('Catchall Mailaddress', size=64, ),
        'companyfooter': fields.text('Company Footer', ),
        'companysupportmail':fields.char('Support Mailaddress', size=64, required=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
