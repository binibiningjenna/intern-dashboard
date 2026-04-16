from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound, MethodNotAllowed


class InternOnboarding(http.Controller):

    # ========================= START OF ERROR BLOCK =========================
    # CUSTOM ERROR PAGE HELPER
    def _render_error_page(self, code='404', title='Page not found', message='The page you are looking for could not be found.'):
        return request.render(
            'famtech_intern_dashboard.intern_error_page',
            {
                'error_code': code,
                'error_title': title,
                'error_message': message,
                'primary_label': 'Go to Dashboard',
                'primary_url': '/dashboard',
                'secondary_label': 'Go Back',
                'secondary_url': 'javascript:history.back()',
            }
        )
    

    @http.route('/my/intern/profile', type='http', auth='user', website=True)
    def intern_profile(self, **kwargs):
        # Real destination for profile editing
        target_url = '/my/account'

       # Check whether the destination route still exists. If it does not, render the custom error page.
        try:
            request.env['ir.http'].routing_map().bind_to_environ(
                request.httprequest.environ
            ).match(target_url, method='GET')
        except (NotFound, MethodNotAllowed):
            return self._render_error_page(
                code='404',
                title='Page not found',
                message='The profile page is currently unavailable.'
            )

        return request.redirect(target_url)

    @http.route('/my/intern/tasks', type='http', auth='user', website=True)
    def intern_tasks(self, **kwargs):
        # Real destination for tasks page
        target_url = '/my/tasks'

        # Check whether the destination route still exists. If it does not, render the custom error page.
        try:
            request.env['ir.http'].routing_map().bind_to_environ(
                request.httprequest.environ
            ).match(target_url, method='GET')
        except (NotFound, MethodNotAllowed):
            return self._render_error_page(
                code='404',
                title='Page not found',
                message='The tasks page is currently unavailable.'
            )

        return request.redirect(target_url)
    
    # ========================= END OF ERROR BLOCK =========================


    def _is_onboarding_complete(self, employee):
        """Returns True only when all 4 steps are done."""
        return all([
            employee.handbook_reviewed,
            employee.orientation_completed,
            employee.odoo_access_granted,
            employee.first_task_assigned,
        ])

    def _auto_detect_onboarding(self, employee):
        updates = {}

        if not employee.orientation_completed:
            attendance = request.env['famtech.meeting.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
            ], limit=1)
            if attendance:
                updates['orientation_completed'] = True

        if not employee.odoo_access_granted:
            partner = employee.user_id.partner_id
            if partner.phone or partner.mobile:
                updates['odoo_access_granted'] = True

        if not employee.first_task_assigned:
            task = request.env['project.task'].sudo().search([
                ('user_ids', 'in', employee.user_id.ids),
                ('state', '=', '1_done'),
            ], limit=1)
            if task:
                updates['first_task_assigned'] = True

        if updates:
            employee.sudo().write(updates)

    @http.route('/onboarding', type='http', auth='user', website=True)
    def intern_onboarding(self, **kwargs):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True),
        ], limit=1)

        # ACCESS CONTROL - If user is not a valid intern, show custom error page
        if not employee:
            return self._render_error_page(
                code='403',
                title='Access denied',
                message='You do not have permission to access the onboarding page.'
            )

        # Auto-detect progress from existing records (no redirect — page always renders)
        self._auto_detect_onboarding(employee)

        completed = sum([
            bool(employee.handbook_reviewed),
            bool(employee.orientation_completed),
            bool(employee.odoo_access_granted),
            bool(employee.first_task_assigned),
        ])
        progress = int((completed / 4) * 100)

        values = {
            'employee': employee,
            'progress': progress,
            'page_name': 'intern_onboarding',
        }
        return request.render(
            'famtech_intern_dashboard.intern_onboarding_page', values
        )

    @http.route('/onboarding/update', type='http', auth='user',
                website=True, methods=['POST'], csrf=True)
    def update_onboarding(self, **kwargs):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True),
        ], limit=1)

        # ACCESS CONTROL - Prevent non-intern users from updating onboarding
        if not employee:
            return self._render_error_page(
                code='403',
                title='Access denied',
                message='You do not have permission to update onboarding progress.'
            )       

        employee.write({
            'handbook_reviewed': bool(kwargs.get('handbook_reviewed')),
            'orientation_completed': bool(kwargs.get('orientation_completed')),
            'odoo_access_granted': bool(kwargs.get('odoo_access_granted')),
            'first_task_assigned': bool(kwargs.get('first_task_assigned')),
        })

        # Always stay on onboarding page after saving so user can review their progress
        return request.redirect('/onboarding')

    @http.route('/my/intern/handbook/download', type='http', auth='user', website=True)
    def download_handbook(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('is_intern', '=', True),
        ], limit=1)

        # ACCESS CONTROL - If user is not a valid intern, block access
        if not employee:
            return self._render_error_page(
                code='403',
                title='Access denied',
                message='You do not have permission to access the handbook.'
            )        

        if employee and not employee.handbook_reviewed:
            employee.sudo().write({'handbook_reviewed': True})

        return request.redirect(
            'https://famtech-innovative-it-solutions2.odoo.com/knowledge/article/78',
            local=False
        )