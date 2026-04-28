from datetime import timedelta

from odoo import api, fields, models


class InternWeeklyWinnerHistory(models.Model):
    _name = 'intern.weekly.winner.history'
    _description = 'Intern Weekly Winner History'
    _order = 'week_start desc, id desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Intern',
        required=True,
        ondelete='cascade',
        index=True,
    )
    week_start = fields.Date(string='Winner Week Start', required=True, index=True)
    voucher_claimed = fields.Boolean(string='Voucher Claimed', default=False)
    voucher_claimed_at = fields.Datetime(string='Voucher Claimed At', readonly=True)

    _sql_constraints = [
        (
            'intern_weekly_winner_history_unique',
            'unique(employee_id, week_start)',
            'A weekly winner history record already exists for this intern and week.',
        ),
    ]

    @api.model
    def _retention_cutoff(self):
        return fields.Date.today() - timedelta(days=90)

    @api.model
    def _claimed_voucher_cutoff(self):
        return fields.Datetime.now() - timedelta(days=90)

    @api.model
    def _purge_expired_histories(self):
        history_cutoff = self._retention_cutoff()
        claimed_voucher_cutoff = self._claimed_voucher_cutoff()

        self.env['intern.weekly.winner.history'].sudo().search([
            ('week_start', '<', history_cutoff),
        ]).unlink()

        self.env['intern.voucher'].sudo().search([
            ('state', '=', 'claimed'),
            ('claimed_at', '!=', False),
            ('claimed_at', '<', claimed_voucher_cutoff),
        ]).unlink()

    @api.model
    def _cron_purge_expired_histories(self):
        self._purge_expired_histories()
