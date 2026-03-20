from odoo import models, fields, api


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    timesheet_ids = fields.One2many(
        'account.analytic.line',
        'user_id',  
        string="Timesheets",
        compute="_compute_timesheet_ids",
        store=False
    )

    is_intern = fields.Boolean("Is Intern", default=False)
    contracted_hours = fields.Float("Contracted Hours", help="Total hours per contract")
    hours_rendered = fields.Float("Hours Rendered", compute="_compute_hours_rendered", store=True)
    onboarding_checklist = fields.Text("Onboarding Checklist")

    # Evaluation metrics (1-5 scale)
    timeliness_score = fields.Float("Timeliness Score")
    responsiveness_score = fields.Float("Responsiveness Score")
    punctuality_score = fields.Float("Punctuality Score")
    quantity_score = fields.Float("Quantity Score")
    quality_score = fields.Float("Quality Score")
    effectiveness_score = fields.Float("Effectiveness Score")
    efficiency_score = fields.Float("Efficiency Score")
    financial_accuracy_score = fields.Float("Financial Accuracy Score")

    average_score = fields.Float("Average Score", compute="_compute_average_score", store=True)
    tasks_completed = fields.Integer("Tasks Completed", compute="_compute_task_counts", store=True)
    tasks_on_time = fields.Integer("Tasks On Time", compute="_compute_task_counts", store=True)
    messages_response_time = fields.Float("Avg Response Time (hrs)", compute="_compute_response_time", store=True)
    posts_published = fields.Integer("Social Posts", compute="_compute_social_posts", store=True)

    @api.depends('user_id')
    def _compute_timesheet_ids(self):
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

    # HOURS COMPUTATION
    @api.depends('attendance_ids.check_in', 'attendance_ids.check_out', 'timesheet_ids.unit_amount')
    def _compute_hours_rendered(self):
        for emp in self:
            total = 0.0

            # Attendance hours
            for att in emp.attendance_ids:
                if att.check_in and att.check_out:
                    delta = att.check_out - att.check_in
                    total += delta.total_seconds() / 3600.0

            # Timesheet hours
            total += sum(emp.timesheet_ids.mapped('unit_amount'))

            emp.hours_rendered = total

    # SCORE COMPUTATION
    @api.depends(
        'timeliness_score', 'responsiveness_score', 'punctuality_score',
        'quantity_score', 'quality_score', 'effectiveness_score',
        'efficiency_score', 'financial_accuracy_score'
    )
    def _compute_average_score(self):
        for rec in self:
            scores = [
                rec.timeliness_score or 0,
                rec.responsiveness_score or 0,
                rec.punctuality_score or 0,
                rec.quantity_score or 0,
                rec.quality_score or 0,
                rec.effectiveness_score or 0,
                rec.efficiency_score or 0,
                rec.financial_accuracy_score or 0,
            ]

            rec.average_score = sum(scores) / len(scores) if scores else 0

    # TASK METRICS
    @api.depends()
    def _compute_task_counts(self):
        for emp in self:
            tasks = self.env['project.task'].search([
                ('user_ids.employee_id', '=', emp.id)
            ])

            completed_tasks = tasks.filtered(lambda t: t.stage_id.fold)

            emp.tasks_completed = len(completed_tasks)

            emp.tasks_on_time = len(
                completed_tasks.filtered(
                    lambda t: t.date_deadline and t.date_done and t.date_done <= t.date_deadline
                )
            )

    # RESPONSE TIME METRIC
    @api.depends()
    def _compute_response_time(self):
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

    # SOCIAL POSTS METRIC
    @api.depends()
    def _compute_social_posts(self):
        for emp in self:
            if 'social.post' in self.env and emp.user_id:
                posts = self.env['social.post'].search([
                    ('user_id', '=', emp.user_id.id)
                ])
                emp.posts_published = len(posts)
            else:
                emp.posts_published = 0