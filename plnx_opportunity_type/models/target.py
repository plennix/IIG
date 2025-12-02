from odoo import models, fields


class CrmTarget(models.Model):
    _name = 'crm.target'
    _description = 'CRM Target'
    _order = 'date desc, id desc'

    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    date = fields.Date(string='Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Insurance Company')
    total_premium = fields.Float(string='Total Premium')
    lead_line_id = fields.Many2one('crm.lead.line', string='Lead Line', readonly=True, ondelete='cascade')
    lead_id = fields.Many2one(related='lead_line_id.crm_id', string='Lead', store=True, readonly=True)

