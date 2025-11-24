from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_line_ids = fields.One2many(
        'account.commission.line',
        'move_id',
        string='Commission Lines',
        help="Commission lines related to this Invoice"
    )

class AccountCommissionLine(models.Model):
    _name = 'account.commission.line'

    move_id = fields.Many2one('account.move', string='Account Move', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner')
    rate = fields.Float(string='Commission Rate (%)')
    amount = fields.Float(string='Commission Amount', compute='_compute_amount')

    @api.depends('rate', 'move_id.amount_total')
    def _compute_amount(self):
        for line in self:
            line.amount = line.rate * line.move_id.amount_total