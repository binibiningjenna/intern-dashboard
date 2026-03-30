from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime


class InternPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True)
        ], limit=1)
        if 'intern_onboarding_count' in counters:
            values['intern_onboarding_count'] = 1 if employee else 0
        return values

    def _auto_detect_onboarding(self, employee):
        """
        Auto-detect and update onboarding step fields based on real Odoo data.
        Called every time the intern visits the onboarding page.
        Only updates a field if it is not already True (never un-checks a completed step).
        """
        updates = {}

        # ------------------------------------------------------------------
        # STEP 1: Handbook Reviewed
        # Auto-mark as True on first visit to the onboarding page.
        # Once they land here, they are considered to have acknowledged it.
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------
        # STEP 2: Orientation Completed
        # Check if a past calendar event with "orientation" in the name
        # exists and the intern (via their partner) was an attendee.
        # ------------------------------------------------------------------
        if not employee.orientation_completed:
            partner = employee.user_id.partner_id
            now = datetime.now()
            orientation_event = request.env['calendar.event'].sudo().search([
                ('stop', '<=', now),
                ('partner_ids', 'in', partner.ids),
            ], limit=1)
            if orientation_event:
                updates['orientation_completed'] = True

        # ------------------------------------------------------------------
        # STEP 3: Odoo Access / Profile Complete
        # Check if the related user's partner has a phone or mobile filled in.
        # You can extend this check (e.g. job_position, address) as needed.
        # ------------------------------------------------------------------
        if not employee.odoo_access_granted:
            partner = employee.user_id.partner_id
            if partner.phone or partner.mobile:
                updates['odoo_access_granted'] = True

        # ------------------------------------------------------------------
        # STEP 4: First Task Assigned
        # Check if any project.task is assigned to this intern.
        # ------------------------------------------------------------------
        if not employee.first_task_assigned:
            task = request.env['project.task'].sudo().search([
                ('user_ids', 'in', employee.user_id.ids),
                ('state', '=', '1_done'),  # ← use state field, not stage_id.fold
            ], limit=1)
            if task:
                updates['first_task_assigned'] = True

        # Write all detected updates in one call
        if updates:
            employee.sudo().write(updates)

    @http.route(['/my/intern/onboarding'], type='http', auth='user', website=True)
    def portal_intern_onboarding(self, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        if not employee or not employee.is_intern:
            return request.redirect('/my/home')

        # Run auto-detection on every page load
        self._auto_detect_onboarding(employee)

        # Recompute progress after auto-detection
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
        return request.render('famtech_intern_dashboard.portal_intern_onboarding_page', values)

    @http.route(['/my/intern/onboarding/update'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def update_onboarding(self, **kw):
        """
        Manual override — HR or intern can still tick/untick checkboxes.
        Auto-detected steps will be re-detected on next page load anyway.
        """
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True)
        ], limit=1)

        if not employee:
            return request.redirect('/my/home')

        employee.write({
            'handbook_reviewed': bool(kw.get('handbook_reviewed')),
            'orientation_completed': bool(kw.get('orientation_completed')),
            'odoo_access_granted': bool(kw.get('odoo_access_granted')),
            'first_task_assigned': bool(kw.get('first_task_assigned')),
        })

        return request.redirect('/my/intern/onboarding')
    
    @http.route(['/my/intern/handbook/download'], type='http', auth='user', website=True)
    def download_handbook(self, **kw):
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('is_intern', '=', True)
        ], limit=1)

        # Mark handbook as reviewed when they click download
        if employee and not employee.handbook_reviewed:
            employee.sudo().write({'handbook_reviewed': True})

        # Redirect to the actual file
        return request.redirect('https://famtech-innovative-it-solutions2.odoo.com/knowledge/article/78', local=False)
    
    @http.route(['/my/intern/calendar'], type='http', auth='user', website=True)
    def portal_intern_calendar(self, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True)
        ], limit=1)

        if not employee:
            return request.redirect('/my/home')

        partner = employee.user_id.partner_id
        from datetime import datetime
        now = datetime.now()

        # Fetch upcoming events where the intern is an attendee
        events = request.env['calendar.event'].sudo().search([
            ('stop', '>=', now),
            ('partner_ids', 'in', partner.ids),
        ], order='start asc', limit=50)

        values = {
            'employee': employee,
            'events': events,
            'page_name': 'intern_calendar',
        }
        return request.render('famtech_intern_dashboard.portal_intern_calendar_page', values)