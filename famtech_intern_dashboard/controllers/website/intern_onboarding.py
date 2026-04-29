from odoo import http
from odoo.http import request
from ...models.meeting_attendance import ONBOARDING_MEETING_TAG


class InternOnboarding(http.Controller):

    def _is_onboarding_complete(self, employee):
        """Returns True only when all 4 steps are done."""
        return all([
            employee.handbook_reviewed,
            employee.orientation_completed,
            employee.odoo_access_granted,
            employee.first_task_assigned,
        ])
    
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

    def _auto_detect_onboarding(self, employee):
        updates = {}

        if not employee.orientation_completed:
            attendance = request.env['famtech.meeting.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('counts_for_orientation', '=', True),
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

    @http.route('/onboarding/mark_seen', type='json', auth='user')
    def mark_onboarding_seen(self):
        employee = request.env.user.employee_id
        if employee:
            employee.sudo().write({'onboarding_modal_seen': True})
        return {'status': 'ok'}
    
    @http.route('/onboarding', type='http', auth='user', website=True)
    def intern_onboarding(self, **kwargs):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True),
        ], limit=1)

        # Error Handler
        if not employee:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to access the onboarding page.',
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
            'onboarding_meeting_tag': ONBOARDING_MEETING_TAG,
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

        # Error Handler
        if not employee:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to access the onboarding page.',
            )

        # Only the handbook step is manually acknowledged from the website UI.
        # The remaining steps are system-detected and should not be set via POST.
        updates = {}
        onboarding_fields = ('handbook_reviewed',)
        for field_name in onboarding_fields:
            if field_name in kwargs:
                updates[field_name] = bool(kwargs.get(field_name))

        if updates:
            employee.write(updates)

        # Always stay on onboarding page after saving so user can review their progress
        return request.redirect('/onboarding')

    @http.route('/my/intern/handbook/download', type='http', auth='user', website=True)
    def download_handbook(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('is_intern', '=', True),
        ], limit=1)

        if employee and not employee.handbook_reviewed:
            employee.sudo().write({'handbook_reviewed': True})

        return request.redirect(
            'https://famtech-innovative-it-solutions2.odoo.com/knowledge/article/78',
            local=False
        )
