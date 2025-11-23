from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    percentage_field = fields.Boolean(string='Percentage Field', default=False)