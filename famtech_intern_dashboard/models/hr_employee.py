from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date

class HREmployee(models.Model):
    _inherit = 'hr.employee'


    KPI_TARGET_SELECTION = [
        ('0', '0%'),
        ('25', '25%'),
        ('50', '50%'),
        ('75', '75%'),
        ('100', '100%'),
    ]

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
    task_target_monthly = fields.Integer(string="Task Target (Monthly)", required=True)
    contracted_hours = fields.Float("Contracted Hours", help="Total hours per contract")
    hr_contact_id = fields.Many2one('hr.employee', string="HR Contact")
    hours_rendered = fields.Float("Hours Rendered", compute="_compute_hours_rendered", store=True)

    # Onboarding step flags (used by portal onboarding page)
    handbook_reviewed = fields.Boolean("Handbook Reviewed", default=False)
    orientation_completed = fields.Boolean("Orientation Completed", default=False)
    odoo_access_granted = fields.Boolean("Odoo Access Granted", default=False)
    first_task_assigned = fields.Boolean("First Task Assigned", default=False)
    internship_start_date = fields.Date("Internship Start Date")
    internship_end_date = fields.Date("Internship End Date")
    supervisor_id = fields.Many2one('hr.employee', string="Supervisor")
    hours_alert_sent = fields.Boolean("Hours Alert Sent", default=False)
    last_performance_alert_sent = fields.Date("Last Performance Alert Sent")

    # Performance Scores
    timeliness_score = fields.Float("Timeliness Score", readonly=True)
    punctuality_score = fields.Float("Punctuality Score", readonly=True)
    quantity_score = fields.Float("Quantity Score", readonly=True)
    quality_score = fields.Float("Quality Score", readonly=True)
    effectiveness_score = fields.Float("Effectiveness Score", readonly=True)
    efficiency_score = fields.Float("Efficiency Score", readonly=True)
    accuracy_score = fields.Float("Accuracy Score", readonly=True)
    average_score = fields.Float("Average Score", compute="_compute_average_score", store=True, readonly=True)

    # KPI Targets
    timeliness_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Timeliness Target", default='0')
    responsiveness_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Responsiveness Target", default='0')
    punctuality_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Punctuality Target", default='0')
    quantity_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Quantity Target", default='0')
    quality_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Quality Target", default='0')
    effectiveness_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Effectiveness Target", default='0')
    efficiency_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Efficiency Target", default='0')
    accuracy_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Accuracy Target", default='0')

    timeliness_target_score = fields.Float("Timeliness Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    responsiveness_target_score = fields.Float("Responsiveness Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    punctuality_target_score = fields.Float("Punctuality Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    quantity_target_score = fields.Float("Quantity Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    quality_target_score = fields.Float("Quality Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    effectiveness_target_score = fields.Float("Effectiveness Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    efficiency_target_score = fields.Float("Efficiency Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)
    accuracy_target_score = fields.Float("Accuracy Target Score", compute="_compute_kpi_target_scores", store=True, readonly=True)

    timeliness_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Timeliness Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    responsiveness_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Responsiveness Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    punctuality_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Punctuality Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    quantity_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Quantity Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    quality_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Quality Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    effectiveness_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Effectiveness Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    efficiency_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Efficiency Result", compute="_compute_kpi_target_results", store=True, readonly=True)
    accuracy_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Accuracy Result", compute="_compute_kpi_target_results", store=True, readonly=True)

    # Responsiveness with Sub-categories
    responsiveness_viber = fields.Float("Viber Response", default=0.0, help="Rate responsiveness on Viber (1-5)")
    responsiveness_google_chat = fields.Float("Google Chat Response", default=0.0, help="Rate responsiveness on Google Chat (1-5)")
    responsiveness_gmail = fields.Float("Gmail Response", default=0.0, help="Rate responsiveness on Google Gmail (1-5)")
    responsiveness_zoho_email = fields.Float("Zoho Email Response", default=0.0, help="Rate responsiveness on Zoho Email (1-5)")
    responsiveness_score = fields.Float("Responsiveness Score", compute="_compute_responsiveness_score", store=True, readonly=True, help="Average of Viber, Google Chat, Gmail, and Zoho Email responsiveness scores")

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
                emp.responsiveness_viber,
                emp.responsiveness_google_chat,
                emp.responsiveness_gmail,
                emp.responsiveness_zoho_email,
            ]
            valid = [s for s in scores if s and s > 0]
            emp.responsiveness_score = round(sum(valid) / len(valid), 2) if valid else 0.0

    @api.depends(
        'timeliness_target_percentage',
        'responsiveness_target_percentage',
        'punctuality_target_percentage',
        'quantity_target_percentage',
        'quality_target_percentage',
        'effectiveness_target_percentage',
        'efficiency_target_percentage',
        'accuracy_target_percentage',
    )
    def _compute_kpi_target_scores(self):
        for rec in self:
            rec.timeliness_target_score = rec._target_percentage_to_score(rec.timeliness_target_percentage)
            rec.responsiveness_target_score = rec._target_percentage_to_score(rec.responsiveness_target_percentage)
            rec.punctuality_target_score = rec._target_percentage_to_score(rec.punctuality_target_percentage)
            rec.quantity_target_score = rec._target_percentage_to_score(rec.quantity_target_percentage)
            rec.quality_target_score = rec._target_percentage_to_score(rec.quality_target_percentage)
            rec.effectiveness_target_score = rec._target_percentage_to_score(rec.effectiveness_target_percentage)
            rec.efficiency_target_score = rec._target_percentage_to_score(rec.efficiency_target_percentage)
            rec.accuracy_target_score = rec._target_percentage_to_score(rec.accuracy_target_percentage)

    @api.depends(
        'timeliness_score', 'responsiveness_score', 'punctuality_score', 'quantity_score',
        'quality_score', 'effectiveness_score', 'efficiency_score', 'accuracy_score',
        'timeliness_target_score', 'responsiveness_target_score', 'punctuality_target_score',
        'quantity_target_score', 'quality_target_score', 'effectiveness_target_score',
        'efficiency_target_score', 'accuracy_target_score',
    )
    def _compute_kpi_target_results(self):
        for rec in self:
            rec.timeliness_target_result = rec._evaluate_target_result(rec.timeliness_score, rec.timeliness_target_score)
            rec.responsiveness_target_result = rec._evaluate_target_result(rec.responsiveness_score, rec.responsiveness_target_score)
            rec.punctuality_target_result = rec._evaluate_target_result(rec.punctuality_score, rec.punctuality_target_score)
            rec.quantity_target_result = rec._evaluate_target_result(rec.quantity_score, rec.quantity_target_score)
            rec.quality_target_result = rec._evaluate_target_result(rec.quality_score, rec.quality_target_score)
            rec.effectiveness_target_result = rec._evaluate_target_result(rec.effectiveness_score, rec.effectiveness_target_score)
            rec.efficiency_target_result = rec._evaluate_target_result(rec.efficiency_score, rec.efficiency_target_score)
            rec.accuracy_target_result = rec._evaluate_target_result(rec.accuracy_score, rec.accuracy_target_score)

    def _target_percentage_to_score(self, percentage):
        return round((float(percentage or 0.0) / 100.0) * 5.0, 2)

    def _evaluate_target_result(self, score, target_score):
        return 'success' if (score or 0.0) >= (target_score or 0.0) else 'failed'

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
                rec.timeliness_score,
                rec.responsiveness_score,
                rec.punctuality_score,
                rec.quantity_score,
                rec.quality_score,
                rec.effectiveness_score,
                rec.efficiency_score,
                rec.accuracy_score,
            ]
            valid = [s for s in scores if s and s > 0]
            rec.average_score = sum(valid) / len(valid) if valid else 0.0

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

    @api.model
    def get_contract_vs_rendered_hours_chart_data(self):
        employees = self.search([('is_intern', '=', True)], order='name asc')
        return [
            {
                'employee_name': employee.name,
                'contract_hours': round(employee.contracted_hours or 0.0, 2),
                'contract_days': round((employee.contracted_hours or 0.0) / 8.0, 2),
                'rendered_hours': round(employee.hours_rendered or 0.0, 2),
                'rendered_days': round((employee.hours_rendered or 0.0) / 8.0, 2),
            }
            for employee in employees
        ]

    # PORTAL ACCESS
    def _get_public_fields(self):
        """Extend the list of fields accessible to portal/public users"""
        public_fields = super()._get_public_fields()
        return public_fields | {
            'is_intern',
            'contracted_hours',
            'hours_rendered',
            'onboarding_checklist',
            'handbook_reviewed',
            'orientation_completed',
            'odoo_access_granted',
            'first_task_assigned',
            'internship_start_date',
            'internship_end_date',
            'supervisor_id',
            'timeliness_score',
            'responsiveness_score',
            'punctuality_score',
            'quantity_score',
            'quality_score',
            'effectiveness_score',
            'efficiency_score',
            'accuracy_score',
            'average_score',
        }

    def _cron_check_intern_hours(self):
        """Daily cron: send alerts for hours reached and low performance."""
        interns = self.search([('is_intern', '=', True)])
        for intern in interns:
            # --- Hours reached alert (only send once) ---
            if (intern.contracted_hours
                    and intern.hours_rendered >= intern.contracted_hours
                    and not intern.hours_alert_sent):
                template = self.env.ref(
                    'famtech_intern_dashboard.email_template_intern_hours_reached',
                    raise_if_not_found=False
                )
                if template:
                    template.sudo().send_mail(intern.id, force_send=True)
                    intern.sudo().write({'hours_alert_sent': True})

            # --- Low performance alert (weekly, score between 0 and 2.5) ---
            if intern.average_score and 0 < intern.average_score < 2.5:
                today = date.today()
                last_sent = intern.last_performance_alert_sent
                if not last_sent or (today - last_sent).days >= 7:
                    template = self.env.ref(
                        'famtech_intern_dashboard.email_template_intern_low_performance',
                        raise_if_not_found=False
                    )
                    if template:
                        template.sudo().send_mail(intern.id, force_send=True)
                        intern.sudo().write({'last_performance_alert_sent': today})