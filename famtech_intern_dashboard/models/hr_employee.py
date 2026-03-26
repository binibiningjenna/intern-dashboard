from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    # Timesheets
    timesheet_ids = fields.One2many(
        'account.analytic.line',
        'user_id',  
        string="Timesheets",
        compute="_compute_timesheet_ids",
        store=False
    )

    # Intern Fields
    is_intern = fields.Boolean("Is Intern", default=False)
    task_target_monthly = fields.Integer(string="Task Target (Monthly)",required=True)
    contracted_hours = fields.Float("Contracted Hours", help="Total hours per contract")
    hours_rendered = fields.Float("Hours Rendered", compute="_compute_hours_rendered", store=True)
    onboarding_checklist = fields.Text("Onboarding Checklist")

    # Performance Scores
    timeliness_score = fields.Float("Timeliness Score", readonly=True)
    punctuality_score = fields.Float("Punctuality Score", readonly=True)
    quantity_score = fields.Float("Quantity Score", readonly=True)
    quality_score = fields.Float("Quality Score", readonly=True)
    effectiveness_score = fields.Float("Effectiveness Score", readonly=True)
    efficiency_score = fields.Float("Efficiency Score", readonly=True)
    accuracy_score = fields.Float("Accuracy Score", readonly=True)
    average_score = fields.Float("Average Score", compute="_compute_average_score", store=True, readonly=True)

    # Responsiveness with Sub-categories
    responsiveness_viber = fields.Float("Viber Response", default=5.0, help="Rate responsiveness on Viber (1-5)")
    responsiveness_google_chat = fields.Float("Google Chat Response", default=5.0, help="Rate responsiveness on Google Chat (1-5)")
    responsiveness_gmail = fields.Float("Gmail Response", default=5.0, help="Rate responsiveness on Google Gmail (1-5)")
    responsiveness_zoho_email = fields.Float("Zoho Email Response", default=5.0, help="Rate responsiveness on Zoho Email (1-5)")
    responsiveness_score = fields.Float("Responsiveness Score", compute="_compute_responsiveness_score", store=True, readonly=True,
        help="Average of Viber, Google Chat, Gmail, and Zoho Email responsiveness scores"
    )

    # Task Metrics
    tasks_completed = fields.Integer("Tasks Completed", compute="_compute_task_counts", store=True)
    tasks_on_time = fields.Integer("Tasks On Time", compute="_compute_task_counts", store=True)
    messages_response_time = fields.Float("Avg Response Time (hrs)", compute="_compute_response_time", store=True)
    posts_published = fields.Integer("Social Posts", compute="_compute_social_posts", store=True)

    # Meeting Attendance Fields
    meeting_attendance_ids = fields.One2many('famtech.meeting.attendance', 'employee_id', string='Meeting Attendance')
    total_meetings = fields.Integer(string='Total Meetings', compute='_compute_meeting_stats', store=False)
    total_lates = fields.Integer(string='Total Lates', compute='_compute_meeting_stats', store=False)

    @api.constrains('responsiveness_viber', 'responsiveness_google_chat', 'responsiveness_gmail', 'responsiveness_zoho_email')
    def _check_responsiveness_scores(self):
        """Ensure responsiveness scores are between 1 and 5"""
        for record in self:
            if record.responsiveness_viber and (record.responsiveness_viber < 1 or record.responsiveness_viber > 5):
                raise ValidationError(_("Viber responsiveness score must be between 1 and 5."))
            if record.responsiveness_google_chat and (record.responsiveness_google_chat < 1 or record.responsiveness_google_chat > 5):
                raise ValidationError(_("Google Chat responsiveness score must be between 1 and 5."))
            if record.responsiveness_gmail and (record.responsiveness_gmail < 1 or record.responsiveness_gmail > 5):
                raise ValidationError(_("Gmail responsiveness score must be between 1 and 5."))
            if record.responsiveness_zoho_email and (record.responsiveness_zoho_email < 1 or record.responsiveness_zoho_email > 5):
                raise ValidationError(_("Zoho Email responsiveness score must be between 1 and 5."))

    @api.depends('responsiveness_viber', 'responsiveness_google_chat', 'responsiveness_gmail', 'responsiveness_zoho_email')
    def _compute_responsiveness_score(self):
        """Calculate average responsiveness score from sub-categories"""
        for emp in self:
            scores = [
                emp.responsiveness_viber or 5.0,
                emp.responsiveness_google_chat or 5.0,
                emp.responsiveness_gmail or 5.0,
                emp.responsiveness_zoho_email or 5.0,
            ]
            emp.responsiveness_score = round(sum(scores) / len(scores), 2)

    @api.depends('user_id')
    def _compute_timesheet_ids(self):
        """Fetch timesheet entries for the employee"""
        Analytic = self.env['account.analytic.line']

        for emp in self:
            if emp.user_id:
                domain = [('user_id', '=', emp.user_id.id)]
            else:
                if 'employee_id' in Analytic._fields:
                    domain = [('employee_id', '=', emp.id)]
                else:
                    domain = []

            emp.timesheet_ids = Analytic.search(domain) if domain else Analytic.browse()

    @api.depends('attendance_ids.check_in', 'attendance_ids.check_out', 'attendance_ids.overtime_status', 'timesheet_ids.unit_amount')
    def _compute_hours_rendered(self):
        """Calculate total hours from APPROVED attendance and timesheets"""
        for emp in self:
            total = 0.0

            for att in emp.attendance_ids:
                is_approved = att.overtime_status == 'approved'
                
                if is_approved and att.check_in and att.check_out:
                    delta = att.check_out - att.check_in
                    total += delta.total_seconds() / 3600.0

            total += sum(emp.timesheet_ids.mapped('unit_amount'))

            emp.hours_rendered = total

    @api.depends(
        'timeliness_score', 'responsiveness_score', 'punctuality_score',
        'quantity_score', 'quality_score', 'effectiveness_score',
        'efficiency_score', 'accuracy_score'
    )
    def _compute_average_score(self):
        """Calculate average of all performance scores"""
        for rec in self:
            scores = [
                rec.timeliness_score or 0,
                rec.responsiveness_score or 0,
                rec.punctuality_score or 0,
                rec.quantity_score or 0,
                rec.quality_score or 0,
                rec.effectiveness_score or 0,
                rec.efficiency_score or 0,
                rec.accuracy_score or 0,
            ]

            rec.average_score = sum(scores) / len(scores) if scores else 0

    @api.depends()
    def _compute_task_counts(self):
        """Count completed tasks and on-time tasks"""
        for emp in self:
            tasks = self.env['project.task'].search([
                ('user_ids.employee_id', '=', emp.id)
            ])

            completed_tasks = tasks.filtered(lambda t: t.stage_id.fold)

            emp.tasks_completed = len(completed_tasks)

            emp.tasks_on_time = len(
                completed_tasks.filtered(
                    lambda t: t.date_deadline and t.date_end and t.date_end <= t.date_deadline
                )
            )

    @api.depends('user_id')
    def _compute_response_time(self):
        """Calculate average response time to messages"""
        for emp in self:

            if not emp.user_id:
                emp.messages_response_time = 0
                continue

            partner = emp.user_id.partner_id

            msgs = self.env['mail.message'].search([
                ('author_id', '=', partner.id)
            ], order='create_date asc', limit=200)

            total_delays = 0.0
            count = 0

            for m in msgs:
                replies = self.env['mail.message'].search([
                    ('parent_id', '=', m.id),
                    ('author_id', '!=', partner.id)
                ], limit=1, order='create_date asc')

                if replies:
                    delta = replies.create_date - m.create_date
                    total_delays += delta.total_seconds() / 3600.0
                    count += 1

            emp.messages_response_time = total_delays / count if count else 0

    @api.depends()
    def _compute_social_posts(self):
        """Count social media posts published"""
        for emp in self:
            if 'social.post' in self.env and emp.user_id:
                posts = self.env['social.post'].search([
                    ('user_id', '=', emp.user_id.id)
                ])
                emp.posts_published = len(posts)
            else:
                emp.posts_published = 0

    @api.depends()
    def _compute_meeting_stats(self):
        """Calculate total meetings attended and number of lates"""
        for emp in self:
            attendances = self.env['famtech.meeting.attendance'].search([
                ('employee_id', '=', emp.id)
            ])
            emp.total_meetings = len(attendances)
            emp.total_lates = len(attendances.filtered(lambda a: a.attendance_status in ['late', 'very_late']))