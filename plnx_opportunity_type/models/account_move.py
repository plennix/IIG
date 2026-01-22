from odoo import models, fields, api,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

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
    _description = 'Account Commission Line'

    move_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade')
    invoice_date = fields.Date(related='move_id.invoice_date', string='Invoice Date', store=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    rate = fields.Float(string='Commission Rate (%)')
    amount = fields.Float(string='Commission Amount', compute='_compute_amount', store=True)
    state = fields.Selection([('not_paid','Not Paid'),
                              ('paid','Paid')],store=True, default='not_paid')

    currency_id = fields.Many2one(related='move_id.currency_id', string='Currency', store=True)
    amount_total = fields.Monetary(related='move_id.amount_total', string='Invoice Total', currency_field='currency_id', store=True)
    commission_percentage = fields.Float(string='Commission %', store=True)
    commission_amount = fields.Float(string='Commission Amount (Calculated)', store=True)

    @api.depends('rate', 'move_id.amount_total')
    def _compute_amount(self):
        for line in self:
            line.amount = line.rate * line.move_id.amount_total

    def _get_quarter_date_range(self, date):
        """Get the start and end date of the quarter for a given date"""
        if not date:
            return None, None
        quarter = (date.month - 1) // 3
        quarter_start = date.replace(month=quarter * 3 + 1, day=1)
        quarter_end = (quarter_start + relativedelta(months=3)) - relativedelta(days=1)
        return quarter_start, quarter_end

    def _get_previous_quarter_range(self, quarter_start, quarter_end):
        """Get the start and end date of the previous quarter"""
        prev_quarter_end = quarter_start - relativedelta(days=1)
        prev_quarter_start = prev_quarter_end.replace(day=1)
        prev_quarter_start = prev_quarter_start - relativedelta(months=2)
        prev_quarter_start = prev_quarter_start.replace(day=1)
        return prev_quarter_start, prev_quarter_end

    def _get_target_percentage_for_quarter(self, partner_id, quarter_start, quarter_end):
        """Get the achievement percentage from crm.target for a partner in a specific quarter"""
        if not partner_id or not quarter_start or not quarter_end:
            return 0.0

        # Find the user linked to this partner
        user = self.env['res.users'].search([('partner_id', '=', partner_id)], limit=1)
        if not user:
            return 0.0

        # Get all crm.target records for this user in the quarter
        targets = self.env['crm.target'].search([
            ('user_id', '=', user.id),
            ('date', '>=', quarter_start),
            ('date', '<=', quarter_end)
        ])

        if not targets:
            return 0.0

        # Calculate the aggregate percentage for the quarter
        total_premium = sum(targets.mapped('total_premium'))
        planned_target = targets[0].planned_target if targets else 0.0

        if planned_target and planned_target > 0:
            return total_premium / planned_target
        return 0.0

    def _get_commission_from_matrix(self, percentage):
        """Get commission percentage from crm.target.matrix based on achievement percentage"""
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Finding commission for percentage: {percentage}")
        if not percentage:
            return 0.0

        matrix = self.env['crm.target.matrix'].search([
            ('from_percentage', '<=', percentage),
            ('to_percentage', '>=', percentage)
        ], limit=1)
        _logger.info(f"found matrix: {matrix}")
        
        

        if matrix:
            return matrix.commission
        return 0.0

    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override read_group to compute commission_percentage and commission_amount at group level based on quarter"""
        res = super(AccountCommissionLine, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )

        # Check if we need to compute commission fields
        needs_commission = 'commission_percentage' in fields or 'commission_amount' in fields

        if needs_commission:
            for line in res:
                commission_pct = 0.0
                commission_amt = 0.0
                total_amount = line.get('amount_total', 0.0)

                # Check if grouped by invoice_date (quarter)
                if 'invoice_date:quarter' in groupby or 'invoice_date' in groupby:
                    # Get the domain for this group to find the records
                    group_domain = line.get('__domain', domain)
                    records = self.search(group_domain)

                    if records:
                        # Get partner from the first record (assuming same partner in group)
                        partner_id = records[0].partner_id.id if records[0].partner_id else False

                        # Get quarter date range from the first record's invoice_date
                        first_date = records[0].invoice_date
                        if first_date and partner_id:
                            quarter_start, quarter_end = self._get_quarter_date_range(first_date)

                            # Get the target percentage for this quarter and partner
                            target_percentage = self._get_target_percentage_for_quarter(
                                partner_id, quarter_start, quarter_end
                            )

                            # Get commission percentage from matrix based on target percentage
                            matrix_commission = self._get_commission_from_matrix(target_percentage)

                            # If commission is 0, try previous quarter
                            if not matrix_commission:
                                prev_quarter_start, prev_quarter_end = self._get_previous_quarter_range(
                                    quarter_start, quarter_end
                                )
                                prev_target_percentage = self._get_target_percentage_for_quarter(
                                    partner_id, prev_quarter_start, prev_quarter_end
                                )
                                matrix_commission = self._get_commission_from_matrix(prev_target_percentage)

                            # commission_percentage = the commission % from matrix
                            commission_pct = matrix_commission

                            # commission_amount = amount_total * commission_percentage / 100
                            if total_amount and matrix_commission:
                                commission_amt = (total_amount * matrix_commission) / 100

                if 'commission_percentage' in fields:
                    line['commission_percentage'] = commission_pct
                if 'commission_amount' in fields:
                    line['commission_amount'] = commission_amt * 100

        return res

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