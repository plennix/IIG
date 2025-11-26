from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_commission = fields.Float(string='Total Commission', readonly=True, store=True)
    commission_count = fields.Integer(string='Commission Count', compute='_compute_commission_count')
    loss_commission_count = fields.Integer(string='Loss Commission Count', compute='_compute_loss_commission_count')

    def _compute_commission_count(self):
        for partner in self:
            commission_lines = self.env['account.commission.line'].search([('partner_id', '=', partner.id)])
            partner.commission_count = len(commission_lines)

    def _compute_loss_commission_count(self):
        for partner in self:
            payments = self.env['account.payment'].search([('partner_id', '=', partner.id), ('with_commission', '=', True), ('payment_type', '=', 'outbound')])
            partner.loss_commission_count = len(payments)
    
    # @api.depends('invoice_ids.commission_line_ids.amount')
    # def _compute_total_commission(self):
    #     for partner in self:
    #         total = 0.0
    #         invoice_ids = self.env['account.move'].search([('state', '=', 'posted')])
    #         for invoice in invoice_ids:
    #             if invoice.state == 'posted' and invoice.commission_line_ids:
    #                 for line in invoice.commission_line_ids:
    #                     if line.partner_id == partner:
    #                         total += line.amount
    #         partner.total_commission = total