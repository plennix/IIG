from odoo import models, fields, api

class CrmStage(models.Model):
    _inherit = 'crm.stage'

    is_proposal = fields.Boolean(default=False)
    is_qualified = fields.Boolean(default=False)