from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_commission = fields.Float(string='Total Commission', compute='_compute_total_commission')

    # @api.depends('invoice_ids.commission_line_ids.amount')
    def _compute_total_commission(self):
        for partner in self:
            total = 0.0
            invoice_ids = self.env['account.move'].search([('state', '=', 'posted')])
            for invoice in invoice_ids:
                if invoice.state == 'posted' and invoice.commission_line_ids:
                    for line in invoice.commission_line_ids:
                        if line.partner_id == partner:
                            total += line.amount
            partner.total_commission = total