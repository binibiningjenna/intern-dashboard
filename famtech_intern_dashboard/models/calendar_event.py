from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    """Extends calendar event to track meeting attendance"""
    
    _inherit = 'calendar.event'
    
    # One2many to attendance records
    attendance_ids = fields.One2many(
        'famtech.meeting.attendance',
        'calendar_event_id',
        string='Attendance Records'
    )
    
    # Count of attendees
    attendance_count = fields.Integer(
        string='Attendance Count',
        compute='_compute_attendance_count'
    )
    
    @api.depends('attendance_ids')
    def _compute_attendance_count(self):
        """Calculate total attendees for each meeting"""
        for event in self:
            event.attendance_count = len(event.attendance_ids)
    
    def get_attendance_data_for_metrics(self):
        """Return attendance data formatted for metric computation"""
        data = []
        for attendance in self.attendance_ids:
            data.append({
                'employee_id': attendance.employee_id.id,
                'employee_name': attendance.employee_id.name,
                'join_time': attendance.join_time,
                'minutes_late': attendance.minutes_late,
                'status': attendance.attendance_status,
            })
        return data