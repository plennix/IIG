from odoo import models, fields, api

class CrmTarget(models.Model):
    _name = 'crm.target'
    _description = 'CRM Target'
    _order = 'date desc, id desc'
    
    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    partner_user_id = fields.Many2one('res.partner', string='Partner', related='user_id.partner_id')
    date = fields.Date(string='Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Insurance Company')
    
    # Change from related to computed with store=True
    planned_target = fields.Float(
        string='Planned Target', 
        compute='_compute_planned_target',
        store=True  # This makes it aggregatable
    )
    
    total_premium = fields.Float(string='Total Premium')
    
    # Percentage field for individual records
    # percentage = fields.Float(
    #     string='Achievement %',
    #     compute='_compute_percentage',
    #     store=True,
    #     help='Percentage of total premium achieved from planned target'
    # )
    
    lead_line_id = fields.Many2one('crm.lead.line', string='Lead Line', readonly=True, ondelete='cascade')
    lead_id = fields.Many2one(related='lead_line_id.crm_id', string='Lead', store=True, readonly=True)
    
    @api.depends('user_id', 'user_id.partner_id', 'user_id.partner_id.planned_target')
    def _compute_planned_target(self):
        for record in self:
            if record.user_id and record.user_id.partner_id:
                record.planned_target = record.user_id.partner_id.planned_target
            else:
                record.planned_target = 0.0
    
    # @api.depends('total_premium', 'planned_target')
    # def _compute_percentage(self):
    #     for record in self:
    #         if record.planned_target and record.planned_target > 0:
    #             record.percentage = (record.total_premium / record.planned_target)
    #         else:
    #             record.percentage = 0.0
    
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     """Override read_group to compute percentage correctly at group level"""
    #     # If grouping by quarter, ensure planned_target is aggregated as max (assuming it's constant per group)
    #     # to avoid summing it incorrectly
    #     if 'quarter' in groupby and 'planned_target' in fields:
    #         # Modify fields to specify aggregation for planned_target
    #         fields = [(f, 'max') if f == 'planned_target' else f for f in fields]
        
    #     res = super(CrmTarget, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    #     if 'percentage' in fields:
    #         for line in res:
    #             if line.get('planned_target') and line['planned_target'] > 0:
    #                 # Calculate percentage from summed total_premium and (now correctly aggregated) planned_target
    #                 line['percentage'] = (line.get('total_premium', 0) / line['planned_target'])
    #             else:
    #                 line['percentage'] = 0.0
    #     return res
