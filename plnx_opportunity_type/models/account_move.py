from odoo import models, fields, api,_ 
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_line_ids = fields.One2many(
        'account.commission.line',
        'move_id',
        string='Commission Lines',
        help="Commission lines related to this Invoice"
    )

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for invoice in self:
            if invoice.move_type == 'out_invoice' and invoice.commission_line_ids:
                for line in invoice.commission_line_ids:
                    if line.partner_id:
                        line.partner_id.total_commission += line.amount
        return res

class AccountCommissionLine(models.Model):
    _name = 'account.commission.line'

    move_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade')
    invoice_date = fields.Date(related='move_id.invoice_date', string='Invoice Date', store=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    rate = fields.Float(string='Commission Rate (%)')
    amount = fields.Float(string='Commission Amount', compute='_compute_amount')
    state = fields.Selection([('not_paid','Not Paid'),
                              ('paid','Paid')],store=True, default='not_paid')

    @api.depends('rate', 'move_id.amount_total')
    def _compute_amount(self):
        for line in self:
            line.amount = line.rate * line.move_id.amount_total

    def action_register_payment(self):
        """Open payment wizard for selected commission lines"""
        total_amount = sum(self.mapped('amount'))
        
        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_id.id,
            'amount': total_amount,
            'ref': f'Commission Payment - {self.partner_id.name}',
        }
        
        payment = self.env['account.payment'].create(payment_vals)
        self.state = 'paid'
        return {
            'name': _('Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }