from odoo import models, fields, api

class CrmTargetMatrix(models.Model):
    _name = 'crm.target.matrix'
    _description = 'Target Matrix'
    _order = 'id asc'

    from_percentage = fields.Float(string='From %')
    to_percentage = fields.Float(string='To %')
    commission = fields.Float(string='Commission %')
    