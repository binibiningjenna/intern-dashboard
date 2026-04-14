from odoo import http
from odoo.http import request

class InternOnboardingController(http.Controller):

    @http.route('/my/intern/onboarding', type='http', auth='user', website=True)
    def intern_onboarding(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

        values = {
            'employee': employee,
            'page_name': 'intern_onboarding'
        }
        return request.render('famtech_intern_dashboard.intern_onboarding', values)