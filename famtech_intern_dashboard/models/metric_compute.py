from odoo import models, fields, api
from datetime import datetime, timedelta
import math

class InternMetricCompute(models.AbstractModel):
    _name = 'intern.metric.compute'
    _description = "Intern Metrics Computation"

    # Helper: smooth scoring curve 
    def _smooth_score(self, ratio):
        if ratio <= 0:
            return 1.0
        if ratio >= 1:
            return 5.0
        log_ratio = math.log10(1 + (9 * ratio))
        return 1 + (4 * log_ratio)

    # Timeliness
    @api.model
    def compute_timeliness_score(self, employee):
        if not employee.user_id:
            return 5.0

        tasks = self.env['project.task'].search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('date_deadline', '!=', False)
        ])

        if not tasks:
            return 5.0

        total_tasks = len(tasks)
        completed_on_time = sum(
            1 for t in tasks
            if t.stage_id.fold
            and t.date_end
            and t.date_deadline
            and t.date_end <= t.date_deadline
        )

        if completed_on_time == 0:
            return 1.0

        ratio = completed_on_time / total_tasks
        return round(self._smooth_score(ratio), 2)

    # Punctuality
    @api.model
    def compute_punctuality_score(self, employee):
        attendances = self.env['famtech.meeting.attendance'].search([
            ('employee_id', '=', employee.id)
        ])
        
        if not attendances:
            return 5.0
        
        late_count = len(attendances.filtered(lambda a: a.attendance_status in ['late', 'very_late']))
        raw_score = 5 - (late_count * 0.5)
        final_score = max(1.0, min(5.0, raw_score))
        
        return final_score

    # Quantity
    @api.model
    def compute_quantity_score(self, employee, period_days=30):
        if not employee.user_id:
            return 5.0

        period_start = fields.Datetime.now() - timedelta(days=period_days)

        assigned_tasks = self.env['project.task'].search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('create_date', '>=', period_start),
        ])

        completed_tasks = self.env['project.task'].search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('date_end', '>=', period_start),
            ('stage_id.fold', '=', True),
        ])

        assigned_count = len(assigned_tasks)
        completed_count = len(completed_tasks)

        if assigned_count == 0:
            return 5.0

        if completed_count == 0:
            return 1.0

        target = employee.task_target_monthly
        if not target:
            return 5.0

        ratio = completed_count / target
        score_ratio = min(ratio, 1.0)
        return round(self._smooth_score(score_ratio), 2)
    
    # Quality
    @api.model
    def compute_quality_score(self, employee):
        if not employee.user_id:
            return 5.0

        tasks = self.env['project.task'].search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('qa_score', '!=', False)
        ])

        if not tasks:
            return 5.0
        
        avg = sum(t.qa_score for t in tasks) / len(tasks)
        return round(max(1.0, min(5.0, avg)), 2)

    # Effectiveness
    @api.model
    def compute_effectiveness_score(self, employee):
        if not employee.user_id:
            return 0.0

        user_id = employee.user_id.id
        leads = self.env['crm.lead'].with_context(active_test=False).search([
            ('user_id', '=', user_id),
        ])

        total = len(leads)
        if total == 0:
            return 5.0

        won = sum(1 for l in leads if l.stage_id and l.stage_id.is_won)
        ratio = won / total
        return round(self._smooth_score(ratio), 2)

    # Efficiency
    @api.model
    def compute_efficiency_score(self, employee):
        if not employee.user_id:
            return 5.0

        user_id = employee.user_id.id
        tasks = self.env['project.task'].search([
            ('user_ids', 'in', [user_id])
        ])

        if not tasks:
            return 5.0

        efficiency_values = []
        for t in tasks:
            total_planned = t.allocated_hours or 0.0
            num_assignees = len(t.user_ids)
            if num_assignees == 0:
                continue

            planned_per_user = total_planned / num_assignees
            actual = sum(
                line.unit_amount
                for line in t.timesheet_ids
                if line.user_id.id == user_id
            )

            if planned_per_user > 0 and actual > 0:
                ratio = min(planned_per_user / actual, 1.0)
                efficiency_values.append(ratio)

        if not efficiency_values:
            return 5.0

        avg_ratio = sum(efficiency_values) / len(efficiency_values)
        return round(self._smooth_score(avg_ratio), 2)

    # Accuracy 
    @api.model
    def compute_accuracy_score(self, employee):
        """Compute accuracy score based on approved vs submitted requests:"""
        
        total_submitted = 0
        total_approved = 0
        
        # 1. Attendance Filings 
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('overtime_status', '!=', False) 
        ])
        total_submitted += len(attendances)
        total_approved += len(attendances.filtered(lambda a: a.overtime_status == 'approved'))
        
        # 2. Time-Offs 
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id)
        ])
        total_submitted += len(leaves)
        total_approved += len(leaves.filtered(lambda l: l.state == 'validate'))
        
        # 3. General Approvals & Payment Applications (approval module - Enterprise only)
        try:
            approvals = self.env['approval.request'].search([
                ('employee_id', '=', employee.id)
            ])
            
            total_submitted += len(approvals)
            total_approved += len(approvals.filtered(lambda a: a.state == 'approved'))
            
            
        except Exception:
            pass
        
        # 4. Expense App Liquidations
        exps = self.env['hr.expense'].search([
            ('employee_id', '=', employee.id)
        ])
        total_submitted += len(exps)
        total_approved += len(exps.filtered(lambda e: e.state == 'approved'))
        
        if total_submitted == 0:
            return 5.0
        
        ratio = total_approved / total_submitted
        return round(self._smooth_score(ratio), 2)
    
    # Delete meeting attendance records older than 90 days
    @api.model
    def cleanup_old_meeting_attendance(self):
        cutoff = fields.Datetime.now() - timedelta(days=90)
        old_records = self.env['famtech.meeting.attendance'].search([
            ('join_time', '<', cutoff)
        ])
        count = len(old_records)
        if count:
            old_records.unlink()
        return True

    # Cron 
    @api.model
    def compute_all_interns_metrics(self):
        employees = self.env['hr.employee'].search([
            ('is_intern', '=', True)
        ])

        for emp in employees:
            timeliness = self.compute_timeliness_score(emp)
            punctuality = self.compute_punctuality_score(emp)
            quantity = self.compute_quantity_score(emp)
            quality = self.compute_quality_score(emp)
            effectiveness = self.compute_effectiveness_score(emp)
            efficiency = self.compute_efficiency_score(emp)
            accuracy = self.compute_accuracy_score(emp)

            emp.sudo().write({
                'timeliness_score': timeliness,
                'punctuality_score': punctuality,
                'quantity_score': quantity,
                'quality_score': quality,
                'effectiveness_score': effectiveness,
                'efficiency_score': efficiency,
                'accuracy_score': accuracy,
            })
