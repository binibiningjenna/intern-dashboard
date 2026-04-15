import csv
import io
import json

from odoo import fields, http
from odoo.http import request


class InternDashboard(http.Controller):
    def _get_kpi_payload(self, employee):
        evaluations = request.env['intern.evaluation'].sudo().search(
            [('employee_id', '=', employee.id)],
            order='eval_date asc, id asc',
        )

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

        if not timeliness_responsiveness_trend:
            timeliness_responsiveness_trend = [{
                'timeliness': round(employee.timeliness_score or 0.0, 2),
                'responsiveness': round(employee.responsiveness_score or 0.0, 2),
                'evaluation_date': fields.Date.today().strftime('%Y-%m-%d'),
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

    def _get_kpi_csv(self, employee, payload):
        output = io.StringIO()
        writer = csv.writer(output)
        result_labels = dict(employee._fields['timeliness_target_result'].selection)
        writer.writerow([
            'Name',
            'Work Email',
            'Department',
            'Job Position',
            'Contracted Hours',
            'Rendered Hours',
            'Average Score',
            'Timeliness',
            'Responsiveness',
            'Punctuality',
            'Quantity',
            'Quality',
            'Effectiveness',
            'Efficiency',
            'Accuracy',
        ])

        summary = payload['summary']
        writer.writerow([
            employee.name or '',
            employee.work_email or '',
            employee.department_id.name or '',
            employee.job_title or employee.job_id.name or '',
            summary['contracted_hours'],
            summary['rendered_hours'],
            summary['average_score'],
            result_labels.get(employee.timeliness_target_result or 'failed', 'Failed'),
            result_labels.get(employee.responsiveness_target_result or 'failed', 'Failed'),
            result_labels.get(employee.punctuality_target_result or 'failed', 'Failed'),
            result_labels.get(employee.quantity_target_result or 'failed', 'Failed'),
            result_labels.get(employee.quality_target_result or 'failed', 'Failed'),
            result_labels.get(employee.effectiveness_target_result or 'failed', 'Failed'),
            result_labels.get(employee.efficiency_target_result or 'failed', 'Failed'),
            result_labels.get(employee.accuracy_target_result or 'failed', 'Failed'),
        ])
        return output.getvalue()

    def _get_kpi_csv_filename(self, employee):
        report_date = fields.Date.today()
        employee_name = (employee.name or 'No Employee').replace('"', '')
        return f'{employee_name} - Metrics and KPI Results ({report_date}).csv'

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

        csv_data = self._get_kpi_csv(employee, self._get_kpi_payload(employee))
        filename = self._get_kpi_csv_filename(employee)
        headers = [
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ]
        return request.make_response(csv_data, headers=headers)

    @http.route('/my/intern_navbar', type='http', auth='user', website=True)
    def intern_navbar(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee or not employee.is_intern:
            return request.redirect('/my/home')
        return request.render('famtech_intern_dashboard.intern_navbar')
