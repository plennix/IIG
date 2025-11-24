from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commission_line_ids = fields.One2many(
        'sale.commission.line',
        'order_id',
        string='Commission Lines',
        help="Commission lines related to this Sale Order"
    )

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res.update(
            {
                "commission_line_ids": [(0, 0, {
                    'partner_id': line.partner_id.id,
                    'rate': line.rate,
                }) for line in self.commission_line_ids],
            }
        )
        return res

class SaleCommissionLine(models.Model):
    _name = 'sale.commission.line'

    order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner')
    rate = fields.Float(string='Commission Rate (%)')
    amount = fields.Float(string='Commission Amount', compute='_compute_amount')

    @api.depends('rate', 'order_id.amount_total')
    def _compute_amount(self):
        for line in self:
            line.amount = line.rate * line.order_id.amount_total