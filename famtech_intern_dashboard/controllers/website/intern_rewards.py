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

    def _get_datetime_field(self, record, field_names):
        for field_name in field_names:
            if field_name in record._fields:
                return record[field_name]
        return False

    def _get_bool_field(self, record, field_names):
        for field_name in field_names:
            if field_name in record._fields:
                return bool(record[field_name])
        return False

    def _format_title(self, value):
        """Clean voucher titles entered by HR/supervisors."""
        value = (value or '').strip()
        if not value:
            return ''
        return ' '.join(word.capitalize() for word in value.split())

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
            },
            {
                'name': 'Consistent Contributor',
                'description': 'Reached 50% of your required rendered hours.',
                'icon': 'lightning-charge-fill',
                'threshold': 50,
                'points_label': '50 pts',
                'unlocked': badge_points >= 50,
            },
            {
                'name': 'High Performer',
                'description': 'Reached 75% of your required rendered hours.',
                'icon': 'graph-up-arrow',
                'threshold': 75,
                'points_label': '75 pts',
                'unlocked': badge_points >= 75,
            },
            {
                'name': 'Elite Intern',
                'description': 'Completed 100% of your required rendered hours.',
                'icon': 'trophy',
                'threshold': 100,
                'points_label': '100 pts',
                'unlocked': badge_points >= 100,
            },
        ]

        return badge_points, badges

    def _build_dynamic_vouchers(self, employee):
        vouchers = []
        Voucher = request.env['intern.voucher'].sudo()
        voucher_records = Voucher.search([('employee_id', '=', employee.id)], order='create_date desc')

        for voucher in voucher_records:
            raw_title = False
            if 'title_display' in voucher._fields:
                raw_title = voucher.title_display
            elif 'title' in voucher._fields:
                raw_title = voucher.title
            elif 'name' in voucher._fields:
                raw_title = voucher.name

            title = self._format_title(raw_title)
            if not title:
                continue

            state = voucher.state if 'state' in voucher._fields else 'available'
            claimed_at = voucher.claimed_at if 'claimed_at' in voucher._fields else False

            vouchers.append({
                'key': 'dynamic_%s' % voucher.id,
                'name': title,
                'icon': 'gift-fill',
                'available': state == 'available',
                'claimed': state == 'claimed',
                'created_at': voucher.create_date,   # ✅ ADD THIS
                'claimed_at': claimed_at,
                'modal_target': '#dynamicVoucherModal' if state == 'available' else False,
            })

        return vouchers

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

        if week_start.month == week_end.month:
            current_week_label = f"Week of {week_start.strftime('%B %d').lstrip('0')} - {week_end.strftime('%d, %Y').lstrip('0')}"
        else:
            current_week_label = f"Week of {week_start.strftime('%B %d').lstrip('0')} - {week_end.strftime('%B %d, %Y').lstrip('0')}"

        # -----------------------------
        # ALL INTERNS / RANKINGS
        # -----------------------------
        all_interns = HrEmployee.search([('is_intern', '=', True)])

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

        badge_points, badges = self._compute_badges_from_hours(
            employee=employee,
            rendered_hours=rendered_hours,
            contracted_hours=contracted_hours,
        )

        avg_score = self._compute_employee_weekly_score(employee)

        # -----------------------------
        # VOUCHERS
        # -----------------------------
        vouchers = []

        is_current_week_winner = bool(
            self._get_bool_field(employee, ['is_weekly_winner']) and
            self._get_date_field(employee, ['weekly_winner_week_start']) == week_start
        )
        weekly_winner_voucher_claimed = bool(
            is_current_week_winner and self._get_bool_field(employee, ['weekly_winner_voucher_claimed'])
        )

        if is_current_week_winner:
            vouchers.append({
                'key': 'weekly_game_prize',
                'name': 'Weekly Game Prize',
                'icon': 'trophy-fill',
                'available': not weekly_winner_voucher_claimed,
                'claimed': weekly_winner_voucher_claimed,
                'claimed_at': self._get_datetime_field(employee, ['weekly_winner_voucher_claimed_at']),
                'modal_target': '#weeklyGamesVoucherModal' if not weekly_winner_voucher_claimed else False,
            })

        vouchers.extend(self._build_dynamic_vouchers(employee))

        available_vouchers = [voucher for voucher in vouchers if voucher['available']]
        claimed_vouchers = [voucher for voucher in vouchers if voucher['claimed']]
        available_vouchers_count = len(available_vouchers)

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
            'available_vouchers': available_vouchers,
            'claimed_vouchers': claimed_vouchers,
            'available_vouchers_count': available_vouchers_count,

            # still available if you need it elsewhere
            'avg_score': avg_score,
        })
