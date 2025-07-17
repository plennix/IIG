from odoo import models, fields, api

class CRM(models.Model):
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

    
    crm_line_ids = fields.One2many('crm.lead.line','crm_id' ,string='Operation', copy=True)

    

    @api.depends('ind_value','ind_rate')
    def _compute_premium(self):
        self.ind_premium = 0.0
        for rec in self:
            rec.ind_premium = rec.ind_value * rec.ind_rate


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
    