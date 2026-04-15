from datetime import datetime

from odoo import api, fields, models


class InternEvaluation(models.Model):
    _name = "intern.evaluation"
    _description = "Intern Evaluation"
    _rec_name = "eval_date"
    _order = "eval_date desc, id desc"

    KPI_TARGET_SELECTION = [
        ('0', '0%'),
        ('25', '25%'),
        ('50', '50%'),
        ('75', '75%'),
        ('100', '100%'),
    ]

    employee_id = fields.Many2one(
        "hr.employee",
        string="Intern",
        required=True,
        ondelete="cascade",
        domain=[("is_intern", "=", True)],
    )
    eval_date = fields.Date(
        string="Evaluation Date",
        default=fields.Date.today,
        required=True,
    )
    is_weekly_snapshot = fields.Boolean(
        string="Weekly Snapshot",
        default=False,
        help="Marks this evaluation as the official end-of-week snapshot used for trend charts.",
    )

    technical_score = fields.Float(string="Technical Skills")
    communication_score = fields.Float(string="Communication")
    collaboration_score = fields.Float(string="Collaboration")
    timeliness_score = fields.Float(string="Timeliness")
    responsiveness_score = fields.Float(string="Responsiveness")
    punctuality_score = fields.Float(string="Punctuality")
    quantity_score = fields.Float(string="Quantity")
    quality_score = fields.Float(string="Quality")
    effectiveness_score = fields.Float(string="Effectiveness")
    efficiency_score = fields.Float(string="Efficiency")
    financial_accuracy_score = fields.Float(string="Financial Accuracy")

    timeliness_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Timeliness Target")
    responsiveness_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Responsiveness Target")
    punctuality_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Punctuality Target")
    quantity_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Quantity Target")
    quality_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Quality Target")
    effectiveness_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Effectiveness Target")
    efficiency_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Efficiency Target")
    accuracy_target_percentage = fields.Selection(KPI_TARGET_SELECTION, string="Accuracy Target")

    timeliness_target_score = fields.Float(string="Timeliness Target Score", compute="_compute_target_scores", store=True)
    responsiveness_target_score = fields.Float(string="Responsiveness Target Score", compute="_compute_target_scores", store=True)
    punctuality_target_score = fields.Float(string="Punctuality Target Score", compute="_compute_target_scores", store=True)
    quantity_target_score = fields.Float(string="Quantity Target Score", compute="_compute_target_scores", store=True)
    quality_target_score = fields.Float(string="Quality Target Score", compute="_compute_target_scores", store=True)
    effectiveness_target_score = fields.Float(string="Effectiveness Target Score", compute="_compute_target_scores", store=True)
    efficiency_target_score = fields.Float(string="Efficiency Target Score", compute="_compute_target_scores", store=True)
    accuracy_target_score = fields.Float(string="Accuracy Target Score", compute="_compute_target_scores", store=True)

    timeliness_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Timeliness Result", compute="_compute_target_results", store=True)
    responsiveness_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Responsiveness Result", compute="_compute_target_results", store=True)
    punctuality_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Punctuality Result", compute="_compute_target_results", store=True)
    quantity_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Quantity Result", compute="_compute_target_results", store=True)
    quality_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Quality Result", compute="_compute_target_results", store=True)
    effectiveness_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Effectiveness Result", compute="_compute_target_results", store=True)
    efficiency_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Efficiency Result", compute="_compute_target_results", store=True)
    accuracy_target_result = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Accuracy Result", compute="_compute_target_results", store=True)

    avg_score = fields.Float(
        string="Average Score",
        compute="_compute_avg_score",
        store=True,
    )

    tasks_completed = fields.Integer(string="Tasks Completed")
    tasks_on_time = fields.Integer(string="Tasks On Time")
    timeliness_percentage = fields.Float(
        string="On-Time Percentage",
        compute="_compute_timeliness_percentage",
        store=True,
    )

    contract_hours = fields.Float(string="Contract Hours")
    actual_hours = fields.Float(string="Hours Rendered")
    hours_variance = fields.Float(
        string="Hours Variance",
        compute="_compute_hours_variance",
        store=True,
    )

    comments = fields.Text(string="Evaluation Comments")

    @api.model
    def get_timeliness_responsiveness_scatter_data(self):
        latest_by_employee = {}
        evaluations = self.search(
            [("employee_id.is_intern", "=", True)],
            order="eval_date desc, id desc",
        )

        for evaluation in evaluations:
            if evaluation.employee_id.id not in latest_by_employee:
                latest_by_employee[evaluation.employee_id.id] = evaluation

        employees = self.env["hr.employee"].search([("is_intern", "=", True)], order="name asc")
        return [
            {
                "employee_name": employee.name,
                "timeliness": round(employee.timeliness_score or 0.0, 2),
                "responsiveness": round(employee.responsiveness_score or 0.0, 2),
                "evaluation_date": (
                    latest_by_employee[employee.id].eval_date.strftime("%Y-%m-%d")
                    if latest_by_employee.get(employee.id) and latest_by_employee[employee.id].eval_date
                    else False
                ),
            }
            for employee in employees
        ]

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            employee = record.employee_id
            if not employee:
                continue
            record.timeliness_score = employee.timeliness_score
            record.responsiveness_score = employee.responsiveness_score
            record.punctuality_score = employee.punctuality_score
            record.quantity_score = employee.quantity_score
            record.quality_score = employee.quality_score
            record.effectiveness_score = employee.effectiveness_score
            record.efficiency_score = employee.efficiency_score
            record.financial_accuracy_score = employee.accuracy_score
            record.timeliness_target_percentage = employee.timeliness_target_percentage
            record.responsiveness_target_percentage = employee.responsiveness_target_percentage
            record.punctuality_target_percentage = employee.punctuality_target_percentage
            record.quantity_target_percentage = employee.quantity_target_percentage
            record.quality_target_percentage = employee.quality_target_percentage
            record.effectiveness_target_percentage = employee.effectiveness_target_percentage
            record.efficiency_target_percentage = employee.efficiency_target_percentage
            record.accuracy_target_percentage = employee.accuracy_target_percentage
            record.tasks_completed = employee.tasks_completed
            record.tasks_on_time = employee.tasks_on_time
            record.contract_hours = employee.contracted_hours
            record.actual_hours = employee.hours_rendered

    @api.depends(
        "timeliness_target_percentage",
        "responsiveness_target_percentage",
        "punctuality_target_percentage",
        "quantity_target_percentage",
        "quality_target_percentage",
        "effectiveness_target_percentage",
        "efficiency_target_percentage",
        "accuracy_target_percentage",
    )
    def _compute_target_scores(self):
        for record in self:
            record.timeliness_target_score = record._target_percentage_to_score(record.timeliness_target_percentage)
            record.responsiveness_target_score = record._target_percentage_to_score(record.responsiveness_target_percentage)
            record.punctuality_target_score = record._target_percentage_to_score(record.punctuality_target_percentage)
            record.quantity_target_score = record._target_percentage_to_score(record.quantity_target_percentage)
            record.quality_target_score = record._target_percentage_to_score(record.quality_target_percentage)
            record.effectiveness_target_score = record._target_percentage_to_score(record.effectiveness_target_percentage)
            record.efficiency_target_score = record._target_percentage_to_score(record.efficiency_target_percentage)
            record.accuracy_target_score = record._target_percentage_to_score(record.accuracy_target_percentage)

    @api.depends(
        "timeliness_score",
        "responsiveness_score",
        "punctuality_score",
        "quantity_score",
        "quality_score",
        "effectiveness_score",
        "efficiency_score",
        "financial_accuracy_score",
        "timeliness_target_score",
        "responsiveness_target_score",
        "punctuality_target_score",
        "quantity_target_score",
        "quality_target_score",
        "effectiveness_target_score",
        "efficiency_target_score",
        "accuracy_target_score",
    )
    def _compute_target_results(self):
        for record in self:
            record.timeliness_target_result = record._evaluate_target_result(record.timeliness_score, record.timeliness_target_score)
            record.responsiveness_target_result = record._evaluate_target_result(record.responsiveness_score, record.responsiveness_target_score)
            record.punctuality_target_result = record._evaluate_target_result(record.punctuality_score, record.punctuality_target_score)
            record.quantity_target_result = record._evaluate_target_result(record.quantity_score, record.quantity_target_score)
            record.quality_target_result = record._evaluate_target_result(record.quality_score, record.quality_target_score)
            record.effectiveness_target_result = record._evaluate_target_result(record.effectiveness_score, record.effectiveness_target_score)
            record.efficiency_target_result = record._evaluate_target_result(record.efficiency_score, record.efficiency_target_score)
            record.accuracy_target_result = record._evaluate_target_result(record.financial_accuracy_score, record.accuracy_target_score)

    def _target_percentage_to_score(self, percentage):
        return round((float(percentage or 0.0) / 100.0) * 5.0, 2)

    def _evaluate_target_result(self, score, target_score):
        return 'success' if (score or 0.0) >= (target_score or 0.0) else 'failed'

    @api.depends(
        "technical_score",
        "communication_score",
        "collaboration_score",
        "timeliness_score",
        "responsiveness_score",
        "punctuality_score",
        "quantity_score",
        "quality_score",
        "effectiveness_score",
        "efficiency_score",
        "financial_accuracy_score",
    )
    def _compute_avg_score(self):
        for record in self:
            scores = [
                record.technical_score,
                record.communication_score,
                record.collaboration_score,
                record.timeliness_score,
                record.responsiveness_score,
                record.punctuality_score,
                record.quantity_score,
                record.quality_score,
                record.effectiveness_score,
                record.efficiency_score,
                record.financial_accuracy_score,
            ]
            valid_scores = [score for score in scores if score > 0]
            record.avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    @api.depends("tasks_completed", "tasks_on_time")
    def _compute_timeliness_percentage(self):
        for record in self:
            record.timeliness_percentage = (
                (record.tasks_on_time / record.tasks_completed) * 100
                if record.tasks_completed
                else 0.0
            )

    @api.depends("contract_hours", "actual_hours")
    def _compute_hours_variance(self):
        for record in self:
            record.hours_variance = record.actual_hours - record.contract_hours


class InternContractHours(models.Model):
    _name = "intern.contract.hours"
    _description = "Intern Contract Hours"
    _rec_name = "employee_id"
    _order = "year desc, month desc, employee_id"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Intern",
        required=True,
        ondelete="cascade",
        domain=[("is_intern", "=", True)],
    )
    month = fields.Selection(
        [(str(i), f"Month {i}") for i in range(1, 13)],
        string="Month",
        required=True,
    )
    year = fields.Integer(
        string="Year",
        default=lambda self: datetime.now().year,
        required=True,
    )
    contract_hours = fields.Float(string="Contract Hours")
    actual_hours = fields.Float(string="Hours Rendered")
    hours_variance = fields.Float(
        string="Hours Variance",
        compute="_compute_hours_variance",
        store=True,
    )
    attendance_rate = fields.Float(
        string="Attendance Rate %",
        compute="_compute_attendance_rate",
        store=True,
    )

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            employee = record.employee_id
            if not employee:
                continue
            record.contract_hours = employee.contracted_hours
            record.actual_hours = employee.hours_rendered

    @api.depends("contract_hours", "actual_hours")
    def _compute_hours_variance(self):
        for record in self:
            record.hours_variance = record.actual_hours - record.contract_hours

    @api.depends("contract_hours", "actual_hours")
    def _compute_attendance_rate(self):
        for record in self:
            record.attendance_rate = (
                (record.actual_hours / record.contract_hours) * 100
                if record.contract_hours
                else 0.0
            )
