from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class MeetingAttendance(models.Model):
    """Tracks intern attendance and punctuality for meetings"""
    _name = 'famtech.meeting.attendance'
    _description = 'Meeting Attendance Record'
    _order = 'join_time desc'
    _rec_name = 'display_name'
    
    _sql_constraints = [
        ('unique_employee_meeting', 'unique(employee_id, calendar_event_id)', 
         'This intern already has attendance recorded for this meeting. Duplicate attendance is not allowed.')
    ]

    # Relations
    employee_id = fields.Many2one('hr.employee', string='Intern', required=True, 
                                  domain=[('is_intern', '=', True)])
    calendar_event_id = fields.Many2one('calendar.event', string='Meeting', required=True,
                                        ondelete='cascade')
    
    # Timing fields
    join_time = fields.Datetime(
        string='Join Time', 
        required=True, 
        default=fields.Datetime.now,
        readonly=True
    )
    meeting_scheduled_start = fields.Datetime(string='Scheduled Start', related='calendar_event_id.start', store=True)
    meeting_scheduled_end = fields.Datetime(string='Scheduled End', related='calendar_event_id.stop', store=True)
    meeting_name = fields.Char(string='Meeting Name', related='calendar_event_id.name', store=True)
    
    # Punctuality metrics
    minutes_late = fields.Integer(string='Minutes Late', compute='_compute_minutes_late', store=True)
    attendance_status = fields.Selection([
        ('ontime', 'On Time'),
        ('late', 'Late (1-10 mins)'),
        ('very_late', 'Very Late (>10 mins)'),
    ], string='Status', compute='_compute_attendance_status', store=True)
    
    # Display name 
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    @api.depends('join_time', 'meeting_scheduled_start')
    def _compute_minutes_late(self):
        """Calculate minutes late based on join time vs meeting start"""
        for record in self:
            if record.join_time and record.meeting_scheduled_start:
                join = fields.Datetime.to_datetime(record.join_time)
                start = fields.Datetime.to_datetime(record.meeting_scheduled_start)
                delta = join - start
                record.minutes_late = max(0, int(delta.total_seconds() / 60))
            else:
                record.minutes_late = 0
    
    @api.depends('minutes_late')
    def _compute_attendance_status(self):
        """Set status: ontime, late, or very_late based on minutes late"""
        for record in self:
            if record.minutes_late <= 0:
                record.attendance_status = 'ontime'
            elif record.minutes_late <= 10:
                record.attendance_status = 'late'
            else:
                record.attendance_status = 'very_late'
    
    @api.depends('employee_id', 'meeting_name', 'join_time')
    def _compute_display_name(self):
        """Generate display name: Employee - Meeting @ Time"""
        for record in self:
            emp_name = record.employee_id.name or 'Unknown'
            meeting = record.meeting_name or 'Meeting'
            join_time_str = fields.Datetime.to_string(record.join_time) if record.join_time else 'Unknown'
            record.display_name = f"{emp_name} - {meeting} @ {join_time_str}"
    
    @api.model
    def cleanup_old_attendance(self):
        """Delete attendance records older than 90 days"""
        cutoff = fields.Datetime.now() - timedelta(days=90)
        old_records = self.search([('join_time', '<', cutoff)])
        count = len(old_records)
        if count:
            old_records.unlink()
            _logger.info(f"Cleaned up {count} old meeting attendance records")
        return True
    
    @api.model_create_multi
    def create(self, vals_list):
        """Enforce time window and prevent duplicate/edited join times"""
        for vals in vals_list:

            meeting = self.env['calendar.event'].browse(vals.get('calendar_event_id'))
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            
            if not meeting:
                continue
            
            if not meeting.start:
                raise ValidationError(_('This meeting has no scheduled start time.'))
            
            # Check for duplicate attendance 
            existing = self.search([
                ('employee_id', '=', employee.id),
                ('calendar_event_id', '=', meeting.id),
            ], limit=1)
            
            if existing:
                raise ValidationError(_(
                    '%(employee)s already has attendance recorded for meeting "%(meeting)s" on %(date)s at %(time)s. '
                    'Duplicate attendance is not allowed.'
                ) % {
                    'employee': employee.name,
                    'meeting': meeting.name,
                    'date': fields.Datetime.to_string(existing.join_time),
                    'time': fields.Datetime.to_string(existing.join_time),
                })
            
            server_now = fields.Datetime.now()
            
            # Time window: 5 min before meeting start until meeting ends
            window_open = meeting.start - timedelta(minutes=5)
            window_close = meeting.stop if meeting.stop else (meeting.start + timedelta(hours=1))
            
            if server_now < window_open:
                # Too early - window not open yet
                minutes_until_open = int((window_open - server_now).total_seconds() / 60)
                open_time_str = fields.Datetime.to_string(window_open)
                raise ValidationError(_(
                    'Attendance window opens at %(open_time)s (%(minutes)d minutes from now). '
                    'You can only record attendance 5 minutes before the meeting starts.'
                ) % {
                    'open_time': open_time_str,
                    'minutes': minutes_until_open,
                })
            
            if server_now > window_close:
                # Too late - meeting already ended
                raise ValidationError(_(
                    'Cannot record attendance. This meeting has already ended at %(end_time)s.'
                ) % {
                    'end_time': fields.Datetime.to_string(window_close),
                })
            
            # Force join_time to server timestamp 
            vals['join_time'] = server_now
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Prevent editing join_time after creation"""
        if 'join_time' in vals:
            raise ValidationError(_('Cannot edit join time. It is automatically recorded and cannot be changed.'))
        return super().write(vals)