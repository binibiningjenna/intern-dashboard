from odoo import http, fields
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

    # Used to determine if the logged-in user is an intern and display onboarding-related UI elements.
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

    # Renders the intern calendar page showing all calendar events where the intern is an attendee.
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
        now = fields.Datetime.context_timestamp(
            request.env.user,
            fields.Datetime.now()
        )

        events = request.env['calendar.event'].sudo().search([
            ('partner_ids', 'in', partner.ids),
        ], order='start asc', limit=50)

        processed_events = []

        for event in events:
            start = event.start
            stop = event.stop

            if start:
                start = fields.Datetime.context_timestamp(request.env.user, start)
            if stop:
                stop = fields.Datetime.context_timestamp(request.env.user, stop)

            processed_events.append({
                'event': event,
                'start': start,
                'stop': stop,
            })

        attendance_records = request.env['famtech.meeting.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
        ])

        processed_attendance = {}

        for rec in attendance_records:
            join_time = rec.join_time

            if join_time:
                join_time = fields.Datetime.context_timestamp(
                    request.env.user,
                    join_time
                )

            processed_attendance[rec.calendar_event_id.id] = {
                'record': rec,
                'join_time': join_time
            }

        attendance_map = processed_attendance

        session_errors = {}

        for ev in events:
            key = 'attendance_error_%s' % ev.id
            if key in request.session:
                session_errors[ev.id] = request.session.pop(key)

        values = {
            'employee': employee,
            'events': processed_events,
            'attendance_map': attendance_map,
            'now': now,
            'session_errors': session_errors,
            'url_error': error or '',
            'page_name': 'intern_calendar',
        }

        return request.render(
            'famtech_intern_dashboard.portal_intern_calendar_page',
            values
        )

    # Creates attendance record and redirects user to the meeting link if available.
    @http.route('/my/intern/join-call/<int:event_id>', type='http', auth='user', website=True)
    def join_call(self, event_id, **kw):
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

    # Logs attendance for events without video call links.
    @http.route('/my/intern/log-attendance/<int:event_id>', type='http', auth='user', website=True)
    def log_attendance_only(self, event_id, **kw):

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