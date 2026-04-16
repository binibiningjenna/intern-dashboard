from odoo import http
from odoo.http import request


class InternDashboard(http.Controller):

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
                # /my/home card: redirect to onboarding if incomplete,
                # dashboard if complete
                if not onboarding_done:
                    return request.redirect('/onboarding')
                return request.redirect('/dashboard')

            # Non-intern portal user
            return request.redirect('/my/home')

        # Public user or internal user without portal access
        return request.redirect('/')

    @http.route('/dashboard', type='http', auth='user', website=True)
    def intern_dashboard(self, **kwargs):
        employee = request.env.user.employee_id.sudo()

        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

        metrics = [
            {'label': 'Timeliness', 'value': employee.timeliness_score, 'icon': 'clock-history'},
            {'label': 'Punctuality', 'value': employee.punctuality_score, 'icon': 'calendar-check'},
            {'label': 'Quantity', 'value': employee.quantity_score, 'icon': 'boxes'},
            {'label': 'Quality', 'value': employee.quality_score, 'icon': 'star'},
            {'label': 'Effectiveness', 'value': employee.effectiveness_score, 'icon': 'bullseye'},
            {'label': 'Efficiency', 'value': employee.efficiency_score, 'icon': 'lightning-charge'},
            {'label': 'Accuracy', 'value': employee.accuracy_score, 'icon': 'check2-circle'},
            {'label': 'Responsiveness', 'value': employee.responsiveness_score, 'icon': 'chat-right-text'},
        ]

        values = {
            'metrics': metrics,
            'page_name': 'intern_dashboard'
        }
        return request.render('famtech_intern_dashboard.intern_dashboard', values)

    @http.route('/my/intern_navbar', type='http', auth='user', website=True)
    def intern_navbar(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee or not employee.is_intern:
            return request.redirect('/my/home')
        return request.render('famtech_intern_dashboard.intern_navbar')