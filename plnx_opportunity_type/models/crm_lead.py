from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    op_type = fields.Selection([
        ('medical','Medical'),
        ('motors','Motors'),
        ('general','General'),
    ], string="Type")

    med_sub_type = fields.Selection([
        ('individuals','Individuals'),
        ('sme','SME'),
        ('groups','Groups'),
    ], string='Sub-Type')

    mot_sub_type = fields.Selection([
        ('individuals','Individuals'),
        ('groups','Groups'),
    ], string='Sub-Type')

    genernal_id = fields.Many2one('general.type', string="Sub-Type")

    med_id = fields.Binary(string="Id")
    proposal_form = fields.Binary(string="Proposal form")

    sme_tax_attach = fields.Binary(string="Tax Id")
    sme_cr_attach = fields.Binary(string="CR Copy")
    sme_membership_attach = fields.Binary(string="Membership list")
    sme_bor_attach = fields.Binary(string="BOR")

    tax_attach = fields.Binary(string="Tax Id")
    cr_attach = fields.Binary(string="CR Copy")
    membership_attach = fields.Binary(string="Membership list")
    bor_attach = fields.Binary(string="BOR")
    others_attach = fields.Binary(string="Others")

    ind_type = fields.Char(string='Type')
    ind_value = fields.Float(string="Value")
    ind_rate = fields.Float(string="Rate")
    ind_premium = fields.Float(string="Premium", compute='_compute_premium')
    commission_rate = fields.Float(string="Commisiion Rate")
    premium_rate = fields.Float(string="Premium Rate")

    contact_type = fields.Selection([
        ('b2b', 'Corporate'),
        ('b2c', 'Individual'),
    ], string="Contact Type")

    tax_id = fields.Char(string='Tax ID')
    national_id = fields.Char(string='National ID')

    multiple_attachments = fields.One2many(
        'ir.attachment',
        'crm_id',
        string='Attachments',
        domain=[('res_model', '=', 'crm.lead')],
        help="Attach multiple files related to this CRM Lead"
    )
    group_multiple_attachments = fields.One2many(
        'ir.attachment',
        'crm_group_id',
        string='Attachments',
        domain=[('res_model', '=', 'crm.lead')],
        help="Attach multiple files related to this CRM Lead"
    )
    is_proposal_stage = fields.Boolean(related='stage_id.is_proposal')
    is_contact_type_stage = fields.Boolean(related='stage_id.is_contact_type_stage')
    crm_line_ids = fields.One2many('crm.lead.line','crm_id' ,string='Operation', copy=True)
    expected_revenue = fields.Monetary('Expected Primary', currency_field='company_currency', tracking=True)

    @api.constrains('tax_id', 'national_id')
    def _check_unique_tax_national_id(self):
        for rec in self:
            if rec.tax_id:
                exists = self.search([
                    ('tax_id', 'ilike', rec.tax_id),
                    ('id', '!=', rec.id)
                ], limit=1)
                if exists:
                    raise ValidationError(
                        _('The Tax ID must be unique!')
                    )
            if rec.national_id:
                same_national = self.search([
                    ('national_id', 'ilike', rec.national_id),
                    ('id', '!=', rec.id)
                ], limit=1)
                if same_national:
                    raise ValidationError(
                        _('The National ID must be unique!')
                    )
    

    @api.depends('ind_value','ind_rate')
    def _compute_premium(self):
        self.ind_premium = 0.0
        for rec in self:
            rec.ind_premium = rec.ind_value * rec.ind_rate

    @api.constrains('stage_id', 'contact_type')
    def _check_contact_type_after_qualified_stage(self):
        for rec in self:
            if not rec.stage_id:
                continue

            qualified_stages = self.env['crm.stage'].search([('is_qualified', '=', True)])
            if not qualified_stages:
                continue

            max_qualified_sequence = max(qualified_stages.mapped('sequence'))
            if rec.stage_id.sequence > max_qualified_sequence and not rec.contact_type:
                raise ValidationError("Please select a Contact Type after qualified stage.")
            
    def action_new_quotation(self):
        action = super(CrmLead, self).action_new_quotation()

        # Always initialize the context if not present
        if not action.get('context'):
            action['context'] = {}

        if self.crm_line_ids:
            product = self.env['product.template'].search([('percentage_field', '=', True)], limit=1)
            if product:
                order_lines = []
                for line in self.crm_line_ids:
                    # Do NOT include non-existent keys like 'force_price' in values!
                    unit_price = line.total_premium * line.percentage
                    order_lines.append(
                        (0, 0, {
                            'product_id': product.id,
                            'product_uom_qty': 1,
                            'price_unit': unit_price,
                        })
                    )
                # Overwrite default_order_line to ensure our price_unit is used
                action['context'].update({'default_order_line': order_lines, 'disable_product_autofill': True})
        return action


class CRMLeadLine(models.Model):
    _name = 'crm.lead.line'

    partner_id = fields.Many2one('res.partner', string="Company Name")
    sending_date = fields.Date(string='Sending Date',default=fields.Date.context_today,)
    receiving_date = fields.Date(string='Receiving Quotation Date')
    proposal_attach = fields.Binary(string="Proposal Attach")
    quotation_attach = fields.Binary(string="Quotation Attach")
    last_update = fields.Char(string='Last Update')
    choosing_one = fields.Boolean(string="Choosing One")
    crm_id = fields.Many2one('crm.lead', string="Lead", store=True)
    type = fields.Selection([
        ('quotation','Quotation'),
        ('addition','Addition'),
        ('delation','Delation'),
    ], string="Type")
    quantity = fields.Integer(string="Quantity")
    percentage = fields.Float(string="Percentage")
    total_premium = fields.Float(string="Total Premium")

