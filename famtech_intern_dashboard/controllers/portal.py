from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime


class InternPortal(CustomerPortal):

    # Custom Error Block
    def _render_error_page(self, code='404', title='Page Not Found', message='The page you are looking for could not be found.'):
        values = {
            'error_code': code,
            'error_title': title,
            'error_message': message,
            'primary_url': '/my/intern/calendar',
            'primary_label': 'Go to Calendar',
            'secondary_url': 'javascript:history.back()',
            'secondary_label': 'Go Back',
        }
        return request.render('famtech_intern_dashboard.intern_error_page', values)

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

    @http.route(['/my/intern/calendar'], type='http', auth='user', website=True)
    def portal_intern_calendar(self, event_id=None, error=None, logged=None, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True)
        ], limit=1)
        
        # Error Handler
        if not employee:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to access the onboarding page.',
            )

        partner = employee.user_id.partner_id
        now = datetime.now()

        # All events — past and upcoming — where intern is attendee
        events = request.env['calendar.event'].sudo().search([
            ('partner_ids', 'in', partner.ids),
        ], order='start asc', limit=50)

        # Build attendance map: event_id → attendance record
        attendance_records = request.env['famtech.meeting.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
        ])
        attendance_map = {rec.calendar_event_id.id: rec for rec in attendance_records}

        # Check for session error from join-call redirect
        session_errors = {}
        for ev in events:
            key = 'attendance_error_%s' % ev.id
            if key in request.session:
                session_errors[ev.id] = request.session.pop(key)

        values = {
            'employee': employee,
            'events': events,
            'attendance_map': attendance_map,
            'now': now,
            'session_errors': session_errors,
            'url_error': error or '',
            'page_name': 'intern_calendar',
        }
        return request.render('famtech_intern_dashboard.portal_intern_calendar_page', values)
    
    @http.route('/my/intern/join-call/<int:event_id>', type='http', auth='user', website=True)
    def join_call(self, event_id, **kw):
        """
        Records attendance then redirects to the video call.
        Uses famtech.meeting.attendance which enforces the time window.
        """
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
        
        event = request.env['calendar.event'].sudo().browse(event_id)
        if not event.exists():
            return self._render_error_page(
                code='404',
                title='Page Not Found',
                message='The requested calendar event could not be found.',
            )

        error = None
        try:
            request.env['famtech.meeting.attendance'].sudo().create({
                'employee_id': employee.id,
                'calendar_event_id': event_id,
            })
        except Exception as e:
            error = str(e)

        # Whether attendance succeeded or failed, redirect to the video call
        # if there's a video URL — attendance error shown on return
        if event.videocall_location:
            if error:
                # Store error in session to show after returning
                request.session['attendance_error_%s' % event_id] = error
            return request.redirect(event.videocall_location, local=False)

        # No video URL — stay on calendar page and show result
        return request.redirect('/my/intern/calendar?event_id=%s&error=%s' % (
            event_id, error or ''
        ))

    @http.route('/my/intern/log-attendance/<int:event_id>', type='http', auth='user', website=True)
    def log_attendance_only(self, event_id, **kw):
        """
        For events without a video call — logs attendance directly.
        """
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
            ('is_intern', '=', True),
        ], limit=1)

        if not employee:
            return self._render_error_page(
                code='403',
                title='Access Denied',
                message='You do not have permission to log attendance for this event.',
            )

        event = request.env['calendar.event'].sudo().browse(event_id)
        if not event.exists():
            return self._render_error_page(
                code='404',
                title='Page Not Found',
                message='The requested calendar event could not be found.',
            )

        error = None
        try:
            request.env['famtech.meeting.attendance'].sudo().create({
                'employee_id': employee.id,
                'calendar_event_id': event_id,
            })
        except Exception as e:
            error = str(e)

        return request.redirect('/my/intern/calendar?logged=%s&error=%s' % (
            event_id, error or ''
        ))