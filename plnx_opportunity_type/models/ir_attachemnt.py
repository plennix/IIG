from odoo import models, fields

class IRAttachment(models.Model):
    _inherit = 'ir.attachment'

    crm_id = fields.Many2one('crm.lead', string='Crm Lead', index=True, ondelete='cascade')
    crm_group_id = fields.Many2one('crm.lead', string='Crm Lead', index=True, ondelete='cascade')