import json

from odoo import fields, http
from odoo.http import request


class InternDashboard(http.Controller):
    def _get_trend_evaluations(self, employee):
        evaluation_model = request.env['intern.evaluation'].sudo()
        weekly_snapshots = evaluation_model.search(
            [
                ('employee_id', '=', employee.id),
                ('is_weekly_snapshot', '=', True),
            ],
            order='eval_date asc, id asc',
        )
        if weekly_snapshots:
            return weekly_snapshots

        return evaluation_model.search(
            [('employee_id', '=', employee.id)],
            order='eval_date asc, id asc',
        )

    def _get_kpi_payload(self, employee):
        evaluations = self._get_trend_evaluations(employee)

        average_score = round(employee.average_score or 0.0, 2)
        contracted_hours = round(employee.contracted_hours or 0.0, 2)
        rendered_hours = round(employee.hours_rendered or 0.0, 2)
        average_score_progress = round(min((average_score / 5.0) * 100, 100), 2) if average_score else 0.0
        hours_progress = round((rendered_hours / contracted_hours) * 100, 2) if contracted_hours else 0.0

        timeliness_responsiveness = [{
            'employee_name': employee.name,
            'timeliness': round(employee.timeliness_score or 0.0, 2),
            'responsiveness': round(employee.responsiveness_score or 0.0, 2),
            'evaluation_date': (
                evaluations[-1].eval_date.strftime('%Y-%m-%d')
                if evaluations and evaluations[-1].eval_date
                else False
            ),
        }]

        timeliness_responsiveness_trend = [
            {
                'timeliness': round(evaluation.timeliness_score or 0.0, 2),
                'responsiveness': round(evaluation.responsiveness_score or 0.0, 2),
                'evaluation_date': evaluation.eval_date.strftime('%Y-%m-%d') if evaluation.eval_date else False,
            }
            for evaluation in evaluations
        ]

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
                return request.redirect('/my/intern_dashboard')

            return request.redirect('/my/home')

        return request.redirect('/')

    @http.route('/my/intern_dashboard', type='http', auth='user', website=True)
    def intern_dashboard(self, **kwargs):
        employee = request.env.user.employee_id.sudo()

        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

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

    @http.route('/my/intern_dashboard/kpi_export', type='http', auth='user', website=True)
    def intern_dashboard_kpi_export(self, **kwargs):
        employee = request.env.user.employee_id.sudo()

        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

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
        if not employee or not employee.is_intern:
            return request.redirect('/my/home')
        return request.render('famtech_intern_dashboard.intern_navbar')
