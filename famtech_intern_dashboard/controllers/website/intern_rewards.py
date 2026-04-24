from datetime import timedelta

from odoo import http, fields
from odoo.http import request


class InternRewards(http.Controller):

    def _get_float_field(self, record, field_names, default=0.0):
        for field_name in field_names:
            if field_name in record._fields:
                value = record[field_name]
                return float(value or 0.0)
        return default

    def _get_date_field(self, record, field_names):
        for field_name in field_names:
            if field_name in record._fields:
                return record[field_name]
        return False

    def _get_bool_field(self, record, field_names):
        for field_name in field_names:
            if field_name in record._fields:
                return bool(record[field_name])
        return False

    def _get_onboarding_done(self, employee):
        onboarding_fields = [
            'handbook_reviewed',
            'orientation_completed',
            'odoo_access_granted',
            'first_task_assigned',
        ]

        existing_fields = [field_name for field_name in onboarding_fields if field_name in employee._fields]
        if not existing_fields:
            return False

        return all(bool(employee[field_name]) for field_name in existing_fields)

    def _compute_employee_weekly_score(self, employee):
        score_fields = [
            'timeliness_score',
            'punctuality_score',
            'quantity_score',
            'quality_score',
            'effectiveness_score',
            'efficiency_score',
            'accuracy_score',
            'responsiveness_score',
        ]

        values = []
        for field_name in score_fields:
            if field_name in employee._fields:
                values.append(float(employee[field_name] or 0.0))

        if not values:
            return 0.0

        return round(sum(values) / len(values), 2)

    def _compute_badges_from_hours(self, employee, rendered_hours, contracted_hours):
        if contracted_hours > 0:
            badge_points = min(int((rendered_hours / contracted_hours) * 100), 100)
        else:
            badge_points = 0

        onboarding_done = self._get_onboarding_done(employee)

        badges = [
            {
                'name': 'Rising Intern',
                'description': 'Completed onboarding and reached the first milestone.',
                'icon': 'stars',
                'threshold': 25,
                'points_label': '25 pts',
                'unlocked': onboarding_done or badge_points >= 25,
                'animate': onboarding_done or badge_points >= 25,
            },
            {
                'name': 'Consistent Contributor',
                'description': 'Reached 50% of your required rendered hours.',
                'icon': 'lightning-charge-fill',
                'threshold': 50,
                'points_label': '50 pts',
                'unlocked': badge_points >= 50,
                'animate': badge_points >= 50,
            },
            {
                'name': 'High Performer',
                'description': 'Reached 75% of your required rendered hours.',
                'icon': 'graph-up-arrow',
                'threshold': 75,
                'points_label': '75 pts',
                'unlocked': badge_points >= 75,
                'animate': badge_points >= 75,
            },
            {
                'name': 'Elite Intern',
                'description': 'Completed 100% of your required rendered hours.',
                'icon': 'trophy',
                'threshold': 100,
                'points_label': '100 pts',
                'unlocked': badge_points >= 100,
                'animate': badge_points >= 100,
            },
        ]

        return badge_points, badges

    @http.route(['/rewards'], type='http', auth='user', website=True)
    def intern_rewards(self, **kwargs):
        user = request.env.user
        HrEmployee = request.env['hr.employee'].sudo()

        employee = HrEmployee.search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True)
        ], limit=1)

        if not employee:
            return request.render('famtech_intern_dashboard.intern_error_403')

        # -----------------------------
        # CURRENT WEEK
        # -----------------------------
        today = fields.Date.context_today(request.env.user)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        current_week_label = "Week of %s - %s" % (
            week_start.strftime('%B %d, %Y'),
            week_end.strftime('%B %d, %Y'),
        )

        # -----------------------------
        # ALL INTERNS / RANKINGS
        # -----------------------------
        all_interns = HrEmployee.search([
            ('is_intern', '=', True)
        ])

        ranked_interns = []
        for emp in all_interns:
            avg_score = self._compute_employee_weekly_score(emp)
            ranked_interns.append({
                'employee': emp,
                'score': avg_score,
            })

        ranked_interns.sort(key=lambda item: item['score'], reverse=True)

        top_interns = []
        for index, item in enumerate(ranked_interns[:3], start=1):
            top_interns.append({
                'rank': index,
                'id': item['employee'].id,
                'name': item['employee'].name,
                'score': item['score'],
            })

        rank = 0
        for index, item in enumerate(ranked_interns, start=1):
            if item['employee'].id == employee.id:
                rank = index
                break

        if not rank:
            rank = len(ranked_interns) + 1

        # -----------------------------
        # WEEKLY WINNER
        # -----------------------------
        weekly_winner_candidates = []
        for emp in all_interns:
            is_weekly_winner = self._get_bool_field(emp, ['is_weekly_winner'])
            winner_week_start = self._get_date_field(emp, ['weekly_winner_week_start'])

            if is_weekly_winner and winner_week_start == week_start:
                weekly_winner_candidates.append(emp)

        weekly_winner = False
        if weekly_winner_candidates:
            weekly_winner = sorted(
                weekly_winner_candidates,
                key=lambda emp: self._compute_employee_weekly_score(emp),
                reverse=True
            )[0]

        weekly_winner_name = weekly_winner.name if weekly_winner else "No winner selected this week"
        weekly_winner_image_url = (
            "/web/image/hr.employee/%s/avatar_1920" % weekly_winner.id
            if weekly_winner else
            "/web/static/img/placeholder.png"
        )

        # WEEKLY WINNER HISTORY
        winner_history_records = HrEmployee.search([
            ('is_intern', '=', True),
            ('is_weekly_winner', '=', True),
            ('weekly_winner_week_start', '!=', False),
        ], order='weekly_winner_week_start desc, name asc', limit=10)

        winner_history = []
        for winner in winner_history_records:
            winner_history.append({
                'name': winner.name,
                'week_start': winner.weekly_winner_week_start.strftime('%B %d, %Y') if winner.weekly_winner_week_start else '',
            })

        # -----------------------------
        # PROGRESS SUMMARY
        # level progress = rendered vs contracted hours
        # -----------------------------
        contracted_hours = self._get_float_field(
            employee,
            ['contracted_hours', 'contract_hours', 'weekly_contracted_hours'],
            default=0.0
        )
        rendered_hours = self._get_float_field(
            employee,
            ['rendered_hours', 'hours_rendered', 'worked_hours'],
            default=0.0
        )

        if contracted_hours > 0:
            progress_percent = min(int((rendered_hours / contracted_hours) * 100), 100)
        else:
            progress_percent = 0

        # -----------------------------
        # BADGES
        # based on rendered vs contracted hours
        # -----------------------------
        badge_points, badges = self._compute_badges_from_hours(
            employee=employee,
            rendered_hours=rendered_hours,
            contracted_hours=contracted_hours,
        )

        avg_score = self._compute_employee_weekly_score(employee)
        # -----------------------------
        # VOUCHERS
        # Weekly Games Winner is automatic but disabled after HR marks it claimed.
        # Other vouchers are controlled from hr.employee.
        # -----------------------------
        is_current_week_winner = bool(
            employee.is_weekly_winner and
            employee.weekly_winner_week_start == week_start
        )
        weekly_winner_voucher_claimed = bool(
            is_current_week_winner and employee.weekly_winner_voucher_claimed
        )

        vouchers = [
            {
                'key': 'weekly_games_winner',
                'name': 'Weekly Games Winner',
                'icon': 'trophy-fill',
                'description': 'Automatically unlocked when you are selected as this week’s winner.',
                'available': is_current_week_winner and not weekly_winner_voucher_claimed,
                'claimed': weekly_winner_voucher_claimed,
                'modal_target': '#weeklyGamesVoucherModal',
            },
            {
                'key': 'webinar_raffle',
                'name': 'Webinar Raffle Winner',
                'icon': 'ticket-detailed-fill',
                'description': 'Available when HR marks you as a webinar raffle winner.',
                'available': bool(employee.reward_webinar_raffle_voucher),
                'claimed': False,
                'modal_target': '#webinarRaffleVoucherModal',
            },
            {
                'key': 'placeholder_1',
                'name': 'Placeholder',
                'icon': 'gift-fill',
                'description': 'Reserved for future reward configuration.',
                'available': bool(employee.reward_placeholder_1_voucher),
                'claimed': False,
                'modal_target': False,
            },
            {
                'key': 'placeholder_2',
                'name': 'Placeholder',
                'icon': 'gift-fill',
                'description': 'Reserved for future reward configuration.',
                'available': bool(employee.reward_placeholder_2_voucher),
                'claimed': False,
                'modal_target': False,
            },
        ]

        available_vouchers_count = len([voucher for voucher in vouchers if voucher['available']])

        return request.render('famtech_intern_dashboard.intern_rewards', {
            'page_name': 'intern_rewards',
            'intern_name': employee.name,

            # Weekly winner
            'current_week_label': current_week_label,
            'weekly_winner_name': weekly_winner_name,
            'weekly_winner_image_url': weekly_winner_image_url,
            'winner_history': winner_history,

            # Top interns + rank
            'top_interns': top_interns,
            'rank': rank,

            # Progress summary
            'progress_percent': progress_percent,
            'rendered_hours': rendered_hours,
            'contracted_hours': contracted_hours,

            # Badges
            'badge_points': badge_points,
            'badges_count': sum(1 for badge in badges if badge['unlocked']),
            'badges': badges,

            # Vouchers
            'vouchers': vouchers,
            'available_vouchers_count': available_vouchers_count,

            # still available if you need it elsewhere
            'avg_score': avg_score,
        })