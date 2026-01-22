from odoo import models, fields, api,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

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
        # Handle both date and datetime objects
        if hasattr(date, 'date'):
            date = date.date()
        quarter = (date.month - 1) // 3
        quarter_start = date.replace(month=quarter * 3 + 1, day=1)
        quarter_end = (quarter_start + relativedelta(months=3)) - relativedelta(days=1)
        return quarter_start, quarter_end

    def _get_target_percentage_for_quarter(self, partner_id, quarter_start, quarter_end):
        """Get the achievement percentage from crm.target for a partner in a specific quarter
        Uses read_group to calculate the same way as crm.target's grouped view"""
        _logger.info("=== Getting target percentage for quarter ===")
        _logger.info("Quarter: %s to %s", quarter_start, quarter_end)
        _logger.info("Partner ID: %s", partner_id)

        if not partner_id or not quarter_start or not quarter_end:
            _logger.info("Missing partner_id or quarter dates, returning 0")
            return 0.0

        # Find the user linked to this partner
        user = self.env['res.users'].search([('partner_id', '=', partner_id)], limit=1)
        _logger.info("Found user: %s (ID: %s)", user.name if user else 'None', user.id if user else 'None')

        if not user:
            return 0.0

        # Use read_group to calculate the same way as crm.target's grouped view
        # This ensures consistency with how the target view calculates percentages
        domain = [
            ('user_id', '=', user.id),
            ('date', '>=', quarter_start),
            ('date', '<=', quarter_end)
        ]

        # Use read_group with the same fields as the target model
        grouped_data = self.env['crm.target'].read_group(
            domain=domain,
            fields=['total_premium:sum', 'planned_target:max', 'percentage'],
            groupby=[],  # No groupby - aggregate all records in the quarter
        )

        _logger.info("read_group result: %s", grouped_data)

        if grouped_data and grouped_data[0]:
            data = grouped_data[0]
            total_premium = data.get('total_premium', 0) or 0
            planned_target_single = data.get('planned_target', 0) or 0
            target_count = data.get('__count', 1) or 1

            # Multiply planned_target by number of targets
            # Each target represents a period, so total planned = planned_target * count
            planned_target = planned_target_single * target_count

            # Calculate percentage
            if planned_target and planned_target > 0:
                percentage = total_premium / planned_target
            else:
                percentage = 0.0

            _logger.info("Total premium: %s, Planned target (single): %s, Target count: %s, Planned target (total): %s, Percentage: %s (%s%%)",
                        total_premium, planned_target_single, target_count, planned_target, percentage, percentage * 100)
            return percentage

        _logger.info("No data found for this quarter")
        return 0.0

    def _get_commission_from_matrix(self, percentage):
        """Get commission percentage from crm.target.matrix based on achievement percentage"""
        if not percentage:
            return 0.0

        # Convert percentage to whole number if it's a decimal (0.7 -> 70)
        # This handles both cases: percentage as decimal (0.7) or as whole number (70)
        percentage_whole = percentage * 100 if percentage < 1 else percentage

        _logger.info("Looking up matrix for percentage: %s (whole: %s)", percentage, percentage_whole)

        # Try with whole number first (e.g., 70 for 70%)
        matrix = self.env['crm.target.matrix'].search([
            ('from_percentage', '<=', percentage_whole),
            ('to_percentage', '>=', percentage_whole)
        ], limit=1)

        if matrix:
            _logger.info("Found matrix entry: from=%s, to=%s, commission=%s",
                        matrix.from_percentage, matrix.to_percentage, matrix.commission)
            return matrix.commission

        # Fallback: try with decimal (e.g., 0.70 for 70%)
        matrix = self.env['crm.target.matrix'].search([
            ('from_percentage', '<=', percentage),
            ('to_percentage', '>=', percentage)
        ], limit=1)

        if matrix:
            _logger.info("Found matrix entry (decimal): from=%s, to=%s, commission=%s",
                        matrix.from_percentage, matrix.to_percentage, matrix.commission)
            return matrix.commission

        # If percentage exceeds all ranges, use the highest commission rate
        # (for cases where achievement > 100%)
        if percentage_whole > 100 or percentage > 1:
            _logger.info("Percentage %s exceeds 100%%, looking for highest matrix entry", percentage_whole)
            highest_matrix = self.env['crm.target.matrix'].search([], order='to_percentage desc', limit=1)
            if highest_matrix:
                _logger.info("Using highest matrix entry: from=%s, to=%s, commission=%s",
                            highest_matrix.from_percentage, highest_matrix.to_percentage, highest_matrix.commission)
                return highest_matrix.commission

        _logger.info("No matrix entry found for percentage %s", percentage_whole)
        return 0.0

    def _get_target_percentage_for_specific_quarter(self, partner_id, quarter_start, quarter_end):
        """
        Get target percentage for a SPECIFIC quarter only.
        Returns (target_percentage, commission_from_matrix)
        Does NOT fallback to other quarters.
        """
        if not partner_id or not quarter_start or not quarter_end:
            return 0.0, 0.0

        target_percentage = self._get_target_percentage_for_quarter(partner_id, quarter_start, quarter_end)
        if target_percentage:
            matrix_commission = self._get_commission_from_matrix(target_percentage)
            return target_percentage, matrix_commission

        return 0.0, 0.0

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

                # Check if grouped by invoice_date (quarter) - handle different groupby formats
                is_quarter_grouped = any(
                    gb in groupby or gb.startswith('invoice_date')
                    for gb in ['invoice_date:quarter', 'invoice_date:month', 'invoice_date:year', 'invoice_date']
                    if gb in groupby
                )

                if not is_quarter_grouped:
                    # Also check for any groupby containing invoice_date
                    is_quarter_grouped = any('invoice_date' in str(gb) for gb in groupby)

                if is_quarter_grouped:
                    # Get the domain for this group to find the records
                    group_domain = line.get('__domain', domain)
                    records = self.search(group_domain, limit=100)  # Limit for performance
                    _logger.info("=== Processing commission group ===")
                    _logger.info("Group domain: %s", group_domain)
                    _logger.info("Found %d records in group", len(records))

                    if records:
                        # Get partner from the first record (assuming same partner in group)
                        partner_id = records[0].partner_id.id if records[0].partner_id else False
                        partner_name = records[0].partner_id.name if records[0].partner_id else 'None'

                        # Get quarter date range from the first record's invoice_date
                        first_date = records[0].invoice_date
                        _logger.info("First record invoice_date: %s, partner: %s (ID: %s)", first_date, partner_name, partner_id)

                        if first_date and partner_id:
                            # Get the quarter range for this specific invoice date
                            quarter_start, quarter_end = self._get_quarter_date_range(first_date)
                            _logger.info("Calculated quarter range: %s to %s", quarter_start, quarter_end)

                            # Get target percentage for THIS SPECIFIC quarter only
                            # Each quarter should use its own achievement data
                            target_percentage, matrix_commission = self._get_target_percentage_for_specific_quarter(
                                partner_id, quarter_start, quarter_end
                            )
                            _logger.info("Result: target_percentage=%s, matrix_commission=%s", target_percentage, matrix_commission)

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