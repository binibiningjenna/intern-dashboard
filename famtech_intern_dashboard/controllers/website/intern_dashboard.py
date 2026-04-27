import json
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from odoo import fields, http
from odoo.http import request


class InternDashboard(http.Controller):
    TREND_WEEK_LENGTH_DAYS = 7

    def _round_score(self, value, digits=2):
        quantize_pattern = "1." + ("0" * digits)
        return float(
            Decimal(str(value or 0.0)).quantize(
                Decimal(quantize_pattern),
                rounding=ROUND_HALF_UP,
            )
        )

    def _format_week_range_label(self, date_from, date_to):
        if not date_from or not date_to:
            return ""
        if date_from == date_to:
            return date_from.strftime('%b %d')
        if date_from.year == date_to.year and date_from.month == date_to.month:
            return f"{date_from.strftime('%b %d')}-{date_to.strftime('%d')}"
        return f"{date_from.strftime('%b %d')} - {date_to.strftime('%b %d')}"
    
    # Custom Error Block
    def _render_error_page(self, code='404', title='Page Not Found', message='The page you are looking for could not be found.'):
        values = {
            'error_code': code,
            'error_title': title,
            'error_message': message,
            'primary_url': '/dashboard',
            'primary_label': 'Go to Dashboard',
            'secondary_url': 'javascript:history.back()',
            'secondary_label': 'Go Back',
        }
        return request.render('famtech_intern_dashboard.intern_error_page', values)

    def _build_weekly_grouped_trend(self, evaluations):
        weekly_groups = []
        evaluations = evaluations.sorted(key=lambda record: (record.eval_date or fields.Date.today(), record.id))
        first_date = evaluations[0].eval_date if evaluations else False
        bucket_size = self.TREND_WEEK_LENGTH_DAYS

        for evaluation in evaluations:
            if not evaluation.eval_date or not first_date:
                continue

            week_index = ((evaluation.eval_date - first_date).days // bucket_size) + 1
            if len(weekly_groups) < week_index:
                week_start = first_date + timedelta(days=(week_index - 1) * bucket_size)
                week_end = week_start + timedelta(days=bucket_size - 1)
                weekly_groups.append({
                    'week_label': f'Week {week_index}',
                    'date_from': week_start.strftime('%Y-%m-%d'),
                    'date_to': week_end.strftime('%Y-%m-%d'),
                    'timeliness_values': [],
                    'responsiveness_values': [],
                    'is_weekly_average': True,
                })

            bucket = weekly_groups[week_index - 1]
            bucket['timeliness_values'].append(evaluation.timeliness_score or 0.0)
            bucket['responsiveness_values'].append(evaluation.responsiveness_score or 0.0)

        return [
            {
                'week_label': bucket['week_label'],
                'week_display_label': f"{bucket['week_label']} ({self._format_week_range_label(fields.Date.from_string(bucket['date_from']), fields.Date.from_string(bucket['date_to']))})",
                'timeliness': self._round_score(sum(bucket['timeliness_values']) / len(bucket['timeliness_values']))
                if bucket['timeliness_values'] else 0.0,
                'responsiveness': self._round_score(sum(bucket['responsiveness_values']) / len(bucket['responsiveness_values']))
                if bucket['responsiveness_values'] else 0.0,
                'evaluation_date': bucket['date_to'],
                'date_from': bucket['date_from'],
                'date_to': bucket['date_to'],
                'is_weekly_average': bucket['is_weekly_average'],
            }
            for bucket in weekly_groups
            if len(bucket['timeliness_values']) >= bucket_size
        ]

    def _build_live_trend_fallback(self, employee):
        has_live_scores = any([
            employee.timeliness_score,
            employee.responsiveness_score,
        ])
        if not has_live_scores:
            return []

        today = fields.Date.today()
        return [{
            'week_label': 'Current Week',
            'week_display_label': f"Current Week ({self._format_week_range_label(today, today)})",
            'timeliness': round(employee.timeliness_score or 0.0, 2),
            'responsiveness': round(employee.responsiveness_score or 0.0, 2),
            'evaluation_date': today.strftime('%Y-%m-%d'),
            'date_from': today.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d'),
            'is_weekly_average': False,
        }]

    def _append_current_week_live_point(self, trend_rows, employee, evaluations):
        live_rows = self._build_live_trend_fallback(employee)
        if not live_rows:
            return trend_rows

        current_live_row = live_rows[0]
        current_date = fields.Date.from_string(current_live_row['evaluation_date'])
        bucket_size = self.TREND_WEEK_LENGTH_DAYS

        if evaluations:
            first_date = evaluations[0].eval_date
            if first_date:
                current_bucket_index = ((current_date - first_date).days // bucket_size) + 1
                current_bucket_start = first_date + timedelta(days=(current_bucket_index - 1) * bucket_size)
                current_bucket_end = current_bucket_start + timedelta(days=bucket_size - 1)
                current_bucket_snapshot_count = len(evaluations.filtered(
                    lambda evaluation: evaluation.eval_date
                    and current_bucket_start <= evaluation.eval_date <= current_bucket_end
                ))
                if current_bucket_snapshot_count >= bucket_size:
                    return trend_rows

        for row in trend_rows:
            row_date_from = fields.Date.from_string(row['date_from']) if row.get('date_from') else False
            row_date_to = fields.Date.from_string(row['date_to']) if row.get('date_to') else False
            if row_date_from and row_date_to and row_date_from <= current_date <= row_date_to:
                return trend_rows

        return trend_rows + [current_live_row]

    def _get_trend_evaluations(self, employee):
        evaluation_model = request.env['intern.evaluation'].sudo()
        return evaluation_model.search(
            [
                ('employee_id', '=', employee.id),
                ('is_weekly_snapshot', '=', False),
            ],
            order='eval_date asc, id asc',
        )

    def _get_kpi_payload(self, employee):
        evaluations = self._get_trend_evaluations(employee)
        timeliness_responsiveness_trend = self._build_weekly_grouped_trend(evaluations)
        if not timeliness_responsiveness_trend:
            timeliness_responsiveness_trend = self._build_live_trend_fallback(employee)
        else:
            timeliness_responsiveness_trend = self._append_current_week_live_point(
                timeliness_responsiveness_trend,
                employee,
                evaluations,
            )

        average_score = round(employee.average_score or 0.0, 2)
        contracted_hours = round(employee.contracted_hours or 0.0, 2)
        rendered_hours = round(employee.hours_rendered or 0.0, 2)
        average_score_progress = round(min((average_score / 5.0) * 100, 100), 2) if average_score else 0.0
        hours_progress = round((rendered_hours / contracted_hours) * 100, 2) if contracted_hours else 0.0

        timeliness_responsiveness = [{
            'employee_name': employee.name,
            'timeliness': round(
                (timeliness_responsiveness_trend[-1]['timeliness'] if timeliness_responsiveness_trend else employee.timeliness_score) or 0.0,
                2,
            ),
            'responsiveness': round(
                (timeliness_responsiveness_trend[-1]['responsiveness'] if timeliness_responsiveness_trend else employee.responsiveness_score) or 0.0,
                2,
            ),
            'evaluation_date': (
                timeliness_responsiveness_trend[-1]['evaluation_date']
                if timeliness_responsiveness_trend
                else False
            ),
        }]

        return {
            'summary': {
                'average_score': average_score,
                'average_score_progress': average_score_progress,
                'contracted_hours': contracted_hours,
                'rendered_hours': rendered_hours,
                'hours_progress': hours_progress,
                'timeliness': round(employee.timeliness_score or 0.0, 2),
                'responsiveness': round(employee.responsiveness_score or 0.0, 2),
            },
            'average_scores': [{
                'employee_name': employee.name,
                'average_score': average_score,
            }],
            'hours': [{
                'employee_name': employee.name,
                'contract_hours': contracted_hours,
                'contract_days': round(contracted_hours / 8.0, 2) if contracted_hours else 0.0,
                'rendered_hours': rendered_hours,
                'rendered_days': round(rendered_hours / 8.0, 2) if rendered_hours else 0.0,
            }],
            'timeliness_responsiveness': timeliness_responsiveness,
            'timeliness_responsiveness_trend': timeliness_responsiveness_trend,
        }

    def _get_kpi_pdf_filename(self, employee):
        report_date = fields.Date.today()
        employee_name = (employee.name or 'No Employee').replace('"', '')
        return f'{employee_name} - Insight Report ({report_date}).pdf'

    def _get_report_date_range(self, employee):
        evaluations = self._get_trend_evaluations(employee)[:1]
        date_to = fields.Date.today()
        date_from = evaluations.eval_date or date_to
        return date_from, date_to

    @http.route(['/my'], type='http', auth='user', website=True)
    def redirect_my(self, **kwargs):
        user = request.env.user

        if user.has_group('base.group_portal'):
            employee = user.employee_id.sudo()

            if employee and employee.is_intern:
                onboarding_done = all([
                    employee.handbook_reviewed,
                    employee.orientation_completed,
                    employee.odoo_access_granted,
                    employee.first_task_assigned,
                ])
                if not onboarding_done:
                    return request.redirect('/onboarding')
                return request.redirect('/dashboard')

            return request.redirect('/my/home')

        return request.redirect('/')

    @http.route('/dashboard', type='http', auth='user', website=True)
    def intern_dashboard(self, **kwargs):
        employee = request.env.user.employee_id.sudo()

        # Error Handler
        if not employee or not employee.is_intern:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to access the intern dashboard.',
            )

        metrics = [
            {
                'label': 'Timeliness',
                'value': employee.timeliness_score,
                'icon': 'clock-history',
                'result': employee.timeliness_target_result,
            },
            {
                'label': 'Punctuality',
                'value': employee.punctuality_score,
                'icon': 'calendar-check',
                'result': employee.punctuality_target_result,
            },
            {
                'label': 'Quantity',
                'value': employee.quantity_score,
                'icon': 'boxes',
                'result': employee.quantity_target_result,
            },
            {
                'label': 'Quality',
                'value': employee.quality_score,
                'icon': 'star',
                'result': employee.quality_target_result,
            },
            {
                'label': 'Effectiveness',
                'value': employee.effectiveness_score,
                'icon': 'bullseye',
                'result': employee.effectiveness_target_result,
            },
            {
                'label': 'Efficiency',
                'value': employee.efficiency_score,
                'icon': 'lightning-charge',
                'result': employee.efficiency_target_result,
            },
            {
                'label': 'Accuracy',
                'value': employee.accuracy_score,
                'icon': 'check2-circle',
                'result': employee.accuracy_target_result,
            },
            {
                'label': 'Responsiveness',
                'value': employee.responsiveness_score,
                'icon': 'chat-right-text',
                'result': employee.responsiveness_target_result,
            },
        ]
        kpi_payload = self._get_kpi_payload(employee)
        values = {
            'employee_name': employee.name,
            'metrics': metrics,
            'kpi_summary': kpi_payload['summary'],
            'kpi_payload_json': json.dumps(kpi_payload),
            'page_name': 'intern_dashboard',
        }

        return request.render('famtech_intern_dashboard.intern_dashboard', values)

    @http.route('/dashboard/kpi_export', type='http', auth='user', website=True)
    def intern_dashboard_kpi_export(self, **kwargs):
        employee = request.env.user.employee_id.sudo()

        # Error Handler
        if not employee or not employee.is_intern:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to export this report.',
            )

        date_from, date_to = self._get_report_date_range(employee)
        wizard = request.env['hr.kpi.dashboard'].sudo().create({
            'date_from': date_from,
            'date_to': date_to,
            'employee_scope': 'single',
            'employee_id': employee.id,
        })
        report = request.env.ref('famtech_intern_dashboard.action_report_hr_kpi_insights').sudo()
        pdf_content, _content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report.report_name,
            res_ids=wizard.id,
        )
        filename = self._get_kpi_pdf_filename(employee)
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', str(len(pdf_content))),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ]
        return request.make_response(pdf_content, headers=headers)

    @http.route('/my/intern_navbar', type='http', auth='user', website=True)
    def intern_navbar(self, **kwargs):
        employee = request.env.user.employee_id
        
        # Error Handler
        if not employee or not employee.is_intern:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to view the intern navigation.',
            )
        
        return request.render('famtech_intern_dashboard.intern_navbar')
