from odoo import http
from odoo.http import request

class InternDashboard(http.Controller):

    @http.route(['/my'], type='http', auth='user', website=True)
    def redirect_my(self, **kwargs):
        user = request.env.user

        if user.has_group('base.group_portal'):
            employee = user.employee_id.sudo()

            # Intern → dashboard
            if employee and employee.is_intern:
                return request.redirect('/my/intern_dashboard')

            # Not Intern → onboarding/home
            return request.redirect('/my/home')

        return request.redirect('/web/login') 

    @http.route('/my/intern_dashboard', type='http', auth='user', website=True)
    def intern_dashboard(self, **kwargs):
        employee = request.env.user.employee_id

        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

        values = {
            'employee_name': employee.name,
        }

        return request.render('famtech_intern_dashboard.intern_dashboard', values)
    
    @http.route('/my/intern_navbar', type='http', auth='user', website=True)
    def intern_navbar(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee or not employee.is_intern:
            return request.redirect('/my/home')
        
        # Note: This route is just an example for rendering the intern navigation bar.
        # All other future intern pages and navigation routes should also be added here.
        # Make sure to reference their XML template IDs to ensure correct rendering.
        return request.render('famtech_intern_dashboard.intern_navbar')