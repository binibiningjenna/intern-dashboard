from odoo import http
from odoo.http import request

class InternRewardsController(http.Controller):

    @http.route('/rewards', type='http', auth='user', website=True)
    def intern_rewards(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

        values = {
            'employee': employee,
            'page_name': 'intern_rewards'
        }
        return request.render('famtech_intern_dashboard.intern_rewards', values)