from odoo import http
from odoo.http import request


class InternDashboard(http.Controller):
    
    # Reusable helper to render the custom error page.
    def _render_error_page(self, code=404, title=None, message=None):
        return request.render('famtech_intern_dashboard.intern_error_page', {
            # Pass dynamic values to the QWeb template
            'error_code': code,

            # Default title fallback based on code
            'error_title': title or (
                'Access Denied' if code == 403 else 'Page Not Found'
            ),

            # Default message fallback based on code
            'error_message': message or (
                'You do not have permission to access this page.'
                if code == 403 else
                'The page you are looking for could not be found.'
            ),
        })

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

        # If user is not an intern, show 403 error page instead of redirect
        if not employee or not employee.is_intern:
            return self._render_error_page(
                code=403,
                message="You are not allowed to access the Intern Dashboard."
            )

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
        
        # Prevent non-intern users from accessing navbar route
        if not employee or not employee.is_intern:
            return self._render_error_page(
                code=403,
                message="You are not allowed to access this page."
            )
        
        return request.render('famtech_intern_dashboard.intern_navbar')