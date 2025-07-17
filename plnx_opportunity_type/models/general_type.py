from odoo import models, fields

class GeneralType(models.Model):
    _name = 'general.type'

    name = fields.Char(string='Name')

    crm_id = fields.Many2one(
        'crm.lead',
        string="Crm lead",
        ondelete='cascade')