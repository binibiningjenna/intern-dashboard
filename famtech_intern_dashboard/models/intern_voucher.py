from odoo import models, fields, api


class InternVoucher(models.Model):
    _name = 'intern.voucher'
    _description = 'Intern Voucher'
    _order = 'create_date desc'

    employee_id = fields.Many2one('hr.employee', string='Intern', required=True, ondelete='cascade')
    title = fields.Char(string='Voucher Title', required=True)
    title_display = fields.Char(string='Display Title', compute='_compute_title_display', store=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('claimed', 'Claimed'),
    ], default='available', required=True)

    claimed_at = fields.Datetime(string='Claimed At', readonly=True)

    @api.depends('title')
    def _compute_title_display(self):
        for record in self:
            record.title_display = (record.title or '').strip().title()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('state') == 'claimed' and not vals.get('claimed_at'):
                vals['claimed_at'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('state') == 'claimed' and not vals.get('claimed_at'):
            vals['claimed_at'] = fields.Datetime.now()

        if vals.get('state') == 'available':
            vals['claimed_at'] = False

        return super().write(vals)