from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    with_commission = fields.Boolean(string='With Commission',default=False)

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for payment in self:
            if payment.with_commission and payment.payment_type == 'outbound':
                payment.partner_id.total_commission -= payment.amount
        return res