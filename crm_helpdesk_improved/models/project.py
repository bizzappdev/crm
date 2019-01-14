# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)

'''
class project(osv.osv):
    _inherit = "project.project"
    _columns = {
        'partner_ids': fields.many2many('ObjectName', 'TableRel', 'src_id', 'dst_id', 'Label', ),
    }
'''

class task(osv.osv):
    _inherit = "project.task"

    def write(self, cr, uid, ids, vals, context=None):
        result = super(task, self).write(cr, uid, ids, vals, context=context)
        if vals.get('stage_id', False):
            crm_helpdesk_pool = self.pool.get('crm.helpdesk')
            crm_helpdesk_pt_pool = self.pool.get('crm.helpdesk.project.task.rel')
            project_tasktype_pool = self.pool.get('project.task.type')
            task_done_id = project_tasktype_pool.search(cr, uid, [('name','=','Done')])
            if vals.get('stage_id') == task_done_id[0]:
                cr.execute("select orig_id from crm_helpdesk_project_task_rel where dest_id in %s",(tuple(ids),))
                crm_ids = cr.fetchall()
                if len(crm_ids)>0:
                    for crm_id in crm_ids[0]:
                        crm_browse = crm_helpdesk_pool.browse(cr, uid, crm_id)
                        tasks_done = True
                        for rel_task in crm_browse.related_task_ids:
                            if rel_task.stage_id.id != task_done_id[0]:
                                tasks_done = False
                        if tasks_done and crm_browse.state != 'done':
                            crm_browse.write({'state': 'todeploy'})
        return result
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
