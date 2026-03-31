import csv
import io
from base64 import b64encode

from odoo import api, fields, models


class HRKPIDashboard(models.TransientModel):
    _name = "hr.kpi.dashboard"
    _description = "HR KPI Dashboard"

    date_from = fields.Date(
        string="Date From",
        default=lambda self: self.env.context.get("date_from") or fields.Date.today(),
    )
    date_to = fields.Date(
        string="Date To",
        default=lambda self: self.env.context.get("date_to") or fields.Date.today(),
    )
    employee_scope = fields.Selection(
        [("all", "All Employees"), ("single", "Select Employee")],
        string="Employee Scope",
        default="all",
        required=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        domain=[("is_intern", "=", True)],
    )
    include_employee_name = fields.Boolean(string="Employee Name", default=True)
    include_work_email = fields.Boolean(string="Work Email", default=True)
    include_department = fields.Boolean(string="Department", default=True)
    include_job_position = fields.Boolean(string="Job Position", default=True)
    include_contracted_hours = fields.Boolean(string="Contracted Hours", default=True)
    include_rendered_hours = fields.Boolean(string="Rendered Hours", default=True)
    include_task_target = fields.Boolean(string="Task Target", default=True)
    include_average_score = fields.Boolean(string="Average Score", default=True)
    include_timeliness = fields.Boolean(string="Timeliness", default=True)
    include_responsiveness = fields.Boolean(string="Responsiveness", default=True)
    include_punctuality = fields.Boolean(string="Punctuality", default=True)
    include_quantity = fields.Boolean(string="Quantity", default=True)
    include_quality = fields.Boolean(string="Quality", default=True)
    include_effectiveness = fields.Boolean(string="Effectiveness", default=True)
    include_efficiency = fields.Boolean(string="Efficiency", default=True)
    include_financial_accuracy = fields.Boolean(string="Accuracy", default=True)
    report_data = fields.Text(string="Report Data", readonly=True)
    export_file = fields.Binary(string="Export File", readonly=True)
    export_filename = fields.Char(string="Export Filename", readonly=True)

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            self.date_from = self.date_to

    @api.onchange("employee_scope")
    def _onchange_employee_scope(self):
        if self.employee_scope != "single":
            self.employee_id = False

    def _validate_scope(self):
        self.ensure_one()
        if self.employee_scope == "single" and not self.employee_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Employee Required",
                    "message": "Please select an employee when exporting a single record.",
                    "sticky": False,
                    "type": "warning",
                },
            }
        return None

    def _get_selected_csv_columns(self):
        columns = []
        if self.include_employee_name:
            columns.append(("Employee Name", lambda evaluation, row: row["employee"].name))
        if self.include_work_email:
            columns.append(("Work Email", lambda evaluation, row: row["work_email"]))
        if self.include_department:
            columns.append(("Department", lambda evaluation, row: row["department"]))
        if self.include_job_position:
            columns.append(("Job Position", lambda evaluation, row: row["job_position"]))
        if self.include_contracted_hours:
            columns.append(("Contracted Hours", lambda evaluation, row: row["total_contract_hours"]))
        if self.include_rendered_hours:
            columns.append(("Rendered Hours", lambda evaluation, row: row["total_rendered_hours"]))
        if self.include_task_target:
            columns.append(("Task Target (Monthly)", lambda evaluation, row: row["task_target_monthly"]))
        if self.include_average_score:
            columns.append(("Average Score", lambda evaluation, row: row["avg_score"]))
        if self.include_timeliness:
            columns.extend([
                ("Timeliness Score", lambda evaluation, row: row["timeliness_score"]),
                ("Timeliness Result", lambda evaluation, row: row["timeliness_result"]),
            ])
        if self.include_responsiveness:
            columns.extend(
                [
                    ("Responsiveness Score", lambda evaluation, row: row["avg_responsiveness"]),
                    ("Responsiveness Result", lambda evaluation, row: row["responsiveness_result"]),
                ]
            )
        if self.include_punctuality:
            columns.extend([
                ("Punctuality Score", lambda evaluation, row: row["avg_punctuality"]),
                ("Punctuality Result", lambda evaluation, row: row["punctuality_result"]),
            ])
        if self.include_quantity:
            columns.extend([
                ("Quantity Score", lambda evaluation, row: row["avg_quantity"]),
                ("Quantity Result", lambda evaluation, row: row["quantity_result"]),
            ])
        if self.include_quality:
            columns.extend([
                ("Quality Score", lambda evaluation, row: row["avg_quality"]),
                ("Quality Result", lambda evaluation, row: row["quality_result"]),
            ])
        if self.include_effectiveness:
            columns.extend([
                ("Effectiveness Score", lambda evaluation, row: row["avg_effectiveness"]),
                ("Effectiveness Result", lambda evaluation, row: row["effectiveness_result"]),
            ])
        if self.include_efficiency:
            columns.extend([
                ("Efficiency Score", lambda evaluation, row: row["avg_efficiency"]),
                ("Efficiency Result", lambda evaluation, row: row["efficiency_result"]),
            ])
        if self.include_financial_accuracy:
            columns.extend([
                ("Accuracy Score", lambda evaluation, row: row["avg_financial_accuracy"]),
                ("Accuracy Result", lambda evaluation, row: row["accuracy_result"]),
            ])
        return columns

    def _filter_employees(self, employees):
        if self.employee_scope == "single" and self.employee_id:
            return employees.filtered(lambda employee: employee.id == self.employee_id.id)
        return employees

    def _get_evaluations(self):
        domain = []
        if self.date_from:
            domain.append(("eval_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("eval_date", "<=", self.date_to))
        if self.employee_scope == "single" and self.employee_id:
            domain.append(("employee_id", "=", self.employee_id.id))
        return self.env["intern.evaluation"].search(
            domain, order="eval_date asc, employee_id asc, id asc"
        )

    def _get_intern_employees(self):
        employees = self.env["hr.employee"].search([("is_intern", "=", True)], order="name asc")
        return self._filter_employees(employees)

    def _build_csv_download(self, csv_data, filename):
        self.write(
            {
                "export_file": b64encode(csv_data.encode("utf-8-sig")),
                "export_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": (
                "/web/content?"
                f"model={self._name}&id={self.id}&field=export_file"
                f"&filename_field=export_filename&download=true"
            ),
            "target": "self",
        }

    def _get_report_employee_names(self):
        self.ensure_one()
        employees = self._get_intern_employees()
        names = [employee.name for employee in employees if employee.name]
        return ", ".join(names) if names else "No Employee"

    def _get_report_date_label(self):
        self.ensure_one()
        report_date = self.date_to or self.date_from or fields.Date.today()
        return str(report_date)

    def _get_metrics_csv_filename(self):
        self.ensure_one()
        return f"{self._get_report_employee_names()} - Metrics and KPI Results ({self._get_report_date_label()}).csv"

    def _get_insight_report_filename(self):
        self.ensure_one()
        return f"{self._get_report_employee_names()} - Insight Report ({self._get_report_date_label()}).pdf"

    def _get_metric_target_map(self, employee):
        return [
            {
                "label": "Timeliness",
                "score": round(employee.timeliness_score or 0.0, 2),
                "target_score": round(employee.timeliness_target_score or 0.0, 2),
                "target_percentage": int(employee.timeliness_target_percentage or 0),
                "result": employee.timeliness_target_result or "failed",
            },
            {
                "label": "Responsiveness",
                "score": round(employee.responsiveness_score or 0.0, 2),
                "target_score": round(employee.responsiveness_target_score or 0.0, 2),
                "target_percentage": int(employee.responsiveness_target_percentage or 0),
                "result": employee.responsiveness_target_result or "failed",
            },
            {
                "label": "Punctuality",
                "score": round(employee.punctuality_score or 0.0, 2),
                "target_score": round(employee.punctuality_target_score or 0.0, 2),
                "target_percentage": int(employee.punctuality_target_percentage or 0),
                "result": employee.punctuality_target_result or "failed",
            },
            {
                "label": "Quantity",
                "score": round(employee.quantity_score or 0.0, 2),
                "target_score": round(employee.quantity_target_score or 0.0, 2),
                "target_percentage": int(employee.quantity_target_percentage or 0),
                "result": employee.quantity_target_result or "failed",
            },
            {
                "label": "Quality",
                "score": round(employee.quality_score or 0.0, 2),
                "target_score": round(employee.quality_target_score or 0.0, 2),
                "target_percentage": int(employee.quality_target_percentage or 0),
                "result": employee.quality_target_result or "failed",
            },
            {
                "label": "Effectiveness",
                "score": round(employee.effectiveness_score or 0.0, 2),
                "target_score": round(employee.effectiveness_target_score or 0.0, 2),
                "target_percentage": int(employee.effectiveness_target_percentage or 0),
                "result": employee.effectiveness_target_result or "failed",
            },
            {
                "label": "Efficiency",
                "score": round(employee.efficiency_score or 0.0, 2),
                "target_score": round(employee.efficiency_target_score or 0.0, 2),
                "target_percentage": int(employee.efficiency_target_percentage or 0),
                "result": employee.efficiency_target_result or "failed",
            },
            {
                "label": "Accuracy",
                "score": round(employee.accuracy_score or 0.0, 2),
                "target_score": round(employee.accuracy_target_score or 0.0, 2),
                "target_percentage": int(employee.accuracy_target_percentage or 0),
                "result": employee.accuracy_target_result or "failed",
            },
        ]

    def _metric_priority(self, metric):
        gap = round((metric["target_score"] or 0.0) - (metric["score"] or 0.0), 2)
        return gap if gap > 0 else 0.0

    def _format_gap_text(self, gap):
        if gap <= 0:
            return "meets or exceeds the target"
        return f"is below target by {gap:.2f} points"

    def _build_metric_analysis(self, metric):
        gap = round((metric["target_score"] or 0.0) - (metric["score"] or 0.0), 2)
        achieved = metric["result"] == "success"
        status_label = "Meeting Target" if achieved else "Below Target"
        guidance_map = {
            "Timeliness": "focus on deadline planning and earlier progress checks",
            "Responsiveness": "improve reply discipline across communication channels",
            "Punctuality": "reinforce attendance discipline and meeting readiness",
            "Quantity": "increase consistent task output against the monthly workload target",
            "Quality": "reduce rework through stronger quality checks before submission",
            "Effectiveness": "improve how outputs align with the intended business outcome",
            "Efficiency": "reduce turnaround time and avoid unnecessary process delays",
            "Accuracy": "tighten detail review to minimize errors in submitted work",
        }
        if achieved:
            description = (
                f"{metric['label']} is performing at {metric['score']:.2f}/5.00 versus the "
                f"configured target of {metric['target_score']:.2f}/5.00 ({metric['target_percentage']}%). "
                "This metric is currently stable and can be sustained through regular monitoring."
            )
        else:
            description = (
                f"{metric['label']} is at {metric['score']:.2f}/5.00 against a target of "
                f"{metric['target_score']:.2f}/5.00 ({metric['target_percentage']}%), leaving a gap of "
                f"{gap:.2f} points. HR may consider coaching that helps the intern "
                f"{guidance_map.get(metric['label'], 'improve performance in this area')}."
            )
        recommended_target = (
            f"Maintain {metric['label']} at or above {metric['target_score']:.2f}/5.00 "
            f"({metric['target_percentage']}%) and preserve the current work habit."
            if achieved
            else (
                f"Raise {metric['label']} to at least {metric['target_score']:.2f}/5.00 "
                f"({metric['target_percentage']}%). This means the intern should "
                f"{guidance_map.get(metric['label'], 'improve performance in this area')}."
            )
        )
        progress_ratio = 0.0
        if metric["target_score"]:
            progress_ratio = min((metric["score"] or 0.0) / metric["target_score"], 1.4)
        return {
            "label": metric["label"],
            "score": metric["score"],
            "target_score": metric["target_score"],
            "target_percentage": metric["target_percentage"],
            "result": metric["result"],
            "status_label": status_label,
            "gap": gap,
            "gap_text": self._format_gap_text(gap),
            "description": description,
            "recommended_target": recommended_target,
            "progress_width": max(min(progress_ratio * 100, 100), 0),
        }

    def _build_overall_insight(self, row):
        analyses = row["metric_analysis"]
        strengths = [item["label"] for item in analyses if item["result"] == "success"]
        focus_areas = sorted(
            [item for item in analyses if item["result"] != "success"],
            key=lambda item: item["gap"],
            reverse=True,
        )
        if not focus_areas:
            return (
                f"{row['employee'].name} is meeting all configured KPI targets for this reporting period. "
                f"The intern's current performance profile shows consistent execution across "
                f"{', '.join(strengths[:4])}{' and other tracked metrics' if len(strengths) > 4 else ''}."
            )

        primary_focus = ", ".join(item["label"] for item in focus_areas[:3])
        strengths_text = ", ".join(strengths[:3]) if strengths else "none of the tracked KPIs yet"
        return (
            f"{row['employee'].name} currently needs support in {primary_focus}. "
            f"While the intern is already meeting targets in {strengths_text}, the remaining KPI gaps indicate "
            "that closer coaching and short-cycle follow-up would help improve overall performance stability."
        )

    def _build_recommended_target_lines(self, row):
        analyses = row["metric_analysis"]
        ordered = sorted(
            analyses,
            key=lambda item: (0 if item["result"] != "success" else 1, -item["gap"], item["label"]),
        )
        return [item["recommended_target"] for item in ordered]

    def _build_group_insights(self, summary_rows):
        if not summary_rows:
            return []

        if len(summary_rows) == 1:
            row = summary_rows[0]
            insights = [row["overall_insight"]]
            if row["attention_metrics"]:
                focus_labels = ", ".join(metric["label"] for metric in row["attention_metrics"][:3])
                insights.append(
                    f"Priority KPI focus areas for this reporting period are {focus_labels}."
                )
            else:
                insights.append(
                    "All tracked KPI categories are currently meeting the configured target."
                )
            return insights

        total = len(summary_rows)
        on_track = [row for row in summary_rows if row["overall_target_status"] == "On Track"]
        needs_attention = [row for row in summary_rows if row["overall_target_status"] != "On Track"]
        insights = [
            (
                f"{len(on_track)} out of {total} interns are currently meeting all configured KPI targets, "
                f"while {len(needs_attention)} still require coaching in at least one metric."
            )
        ]

        if needs_attention:
            focus_counts = {}
            for row in needs_attention:
                for item in row["metric_analysis"]:
                    if item["result"] != "success":
                        focus_counts[item["label"]] = focus_counts.get(item["label"], 0) + 1
            top_focus = sorted(focus_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
            if top_focus:
                insights.append(
                    "The most common coaching priorities are "
                    + ", ".join(f"{label} ({count} interns)" for label, count in top_focus)
                    + "."
                )

        strongest = sorted(summary_rows, key=lambda row: row["avg_score"], reverse=True)[:3]
        if strongest:
            insights.append(
                "Top overall performers based on average score are "
                + ", ".join(
                    f"{row['employee'].name} ({row['avg_score']:.2f})" for row in strongest
                )
                + "."
            )
        return insights

    def _build_group_metric_rankings(self, summary_rows):
        if not summary_rows:
            return []

        rankings = []
        metric_sequence = [
            "Timeliness",
            "Responsiveness",
            "Punctuality",
            "Quantity",
            "Quality",
            "Effectiveness",
            "Efficiency",
            "Accuracy",
        ]

        guidance_map = {
            "Timeliness": "tighten deadline planning, milestone tracking, and earlier progress follow-ups",
            "Responsiveness": "improve turnaround discipline in chats, email, and internal updates",
            "Punctuality": "reinforce attendance consistency and on-time meeting readiness",
            "Quantity": "increase sustainable output volume against assigned workload targets",
            "Quality": "reduce avoidable revisions through stronger quality checks before submission",
            "Effectiveness": "align outputs more closely with the intended business outcome and brief",
            "Efficiency": "shorten turnaround time by removing avoidable process delays",
            "Accuracy": "strengthen detail validation to reduce submission errors",
        }

        metric_map = {}
        for row in summary_rows:
            for metric in row["metric_analysis"]:
                metric_map.setdefault(metric["label"], []).append(
                    {
                        "employee_name": row["employee"].name,
                        "score": metric["score"],
                        "target_score": metric["target_score"],
                        "target_percentage": metric["target_percentage"],
                        "result": metric["result"],
                    }
                )

        for label in metric_sequence:
            entries = metric_map.get(label, [])
            if not entries:
                continue

            ordered_entries = sorted(
                entries,
                key=lambda item: (-item["score"], item["employee_name"].lower()),
            )
            target_score = ordered_entries[0]["target_score"] if ordered_entries else 0.0
            target_percentage = ordered_entries[0]["target_percentage"] if ordered_entries else 0
            avg_score = round(
                sum(item["score"] for item in ordered_entries) / len(ordered_entries), 2
            ) if ordered_entries else 0.0
            below_target = [item for item in ordered_entries if item["result"] != "success"]
            leader = ordered_entries[0]
            trailer = ordered_entries[-1]
            top_score = leader["score"] if ordered_entries else 0.0
            leaders = [item for item in ordered_entries if item["score"] == top_score]
            leader_names = ", ".join(item["employee_name"] for item in leaders)

            grouped_entries = []
            current_group = None
            rank_counter = 0
            for item in ordered_entries:
                if not current_group or item["score"] != current_group["score"]:
                    rank_counter += 1
                    bar_ratio = (item["score"] / 5.0) if 5.0 else 0.0
                    current_group = {
                        "rank": rank_counter,
                        "score": item["score"],
                        "employee_names": [item["employee_name"]],
                        "bar_width": max(min(bar_ratio * 100, 100), 0),
                        "gap": round((target_score or 0.0) - (item["score"] or 0.0), 2),
                    }
                    grouped_entries.append(current_group)
                else:
                    current_group["employee_names"].append(item["employee_name"])

            for group in grouped_entries:
                group["employee_label"] = ", ".join(group["employee_names"])

            if below_target:
                interpretation = (
                    f"{label} currently averages {avg_score:.2f}/5.00 across the group versus a target of "
                    f"{target_score:.2f}/5.00 ({target_percentage}%). {leader_names} {'are' if len(leaders) > 1 else 'is'} leading this metric at "
                    f"{leader['score']:.2f}, while {len(below_target)} out of {len(ordered_entries)} interns are still below target. "
                    f"The widest support need is with {trailer['employee_name']} at {trailer['score']:.2f}/5.00."
                )
                recommended_target = (
                    f"Lift all interns to at least {target_score:.2f}/5.00 ({target_percentage}%) in {label}. "
                    f"Prioritize coaching for the lower-ranked interns and help the team {guidance_map.get(label, 'improve performance in this area')}."
                )
            else:
                interpretation = (
                    f"{label} currently averages {avg_score:.2f}/5.00 across the group, which is at or above the "
                    f"target of {target_score:.2f}/5.00 ({target_percentage}%). {leader_names} {'are' if len(leaders) > 1 else 'is'} leading at "
                    f"{leader['score']:.2f}, and all ranked interns are meeting the expected standard in this category."
                )
                recommended_target = (
                    f"Maintain {label} at or above {target_score:.2f}/5.00 ({target_percentage}%) for all interns "
                    "through regular monitoring and replication of the current best practices."
                )

            rankings.append(
                {
                    "label": label,
                    "entries": grouped_entries,
                    "avg_score": avg_score,
                    "target_score": target_score,
                    "target_percentage": target_percentage,
                    "below_target_count": len(below_target),
                    "interpretation": interpretation,
                    "recommended_target": recommended_target,
                }
            )

        return rankings

    def _get_summary_rows(self, evaluations=None):
        evaluations = evaluations or self._get_evaluations()
        evaluations_by_employee = {}
        for evaluation in evaluations:
            evaluations_by_employee.setdefault(evaluation.employee_id.id, self.env["intern.evaluation"])
            evaluations_by_employee[evaluation.employee_id.id] |= evaluation

        summary_rows = []
        for employee in self._get_intern_employees():
            employee_evaluations = evaluations_by_employee.get(employee.id, self.env["intern.evaluation"])
            evaluation_count = len(employee_evaluations)

            if evaluation_count:
                avg_score = round(sum(employee_evaluations.mapped("avg_score")) / evaluation_count, 2)
                avg_timeliness = round(
                    sum(employee_evaluations.mapped("timeliness_percentage")) / evaluation_count, 2
                )
            else:
                avg_score = round(employee.average_score or 0.0, 2)
                avg_timeliness = round(
                    ((employee.tasks_on_time / employee.tasks_completed) * 100)
                    if employee.tasks_completed
                    else 0.0,
                    2,
                )

            attendance_rate = round(
                ((employee.hours_rendered or 0.0) / (employee.contracted_hours or 1.0) * 100)
                if employee.contracted_hours
                else 0.0,
                2,
            )

            summary_rows.append(
                {
                    "employee": employee,
                    "work_email": employee.work_email or "",
                    "department": employee.department_id.name or "",
                    "job_position": employee.job_title or employee.job_id.name or "",
                    "avg_score": avg_score,
                    "avg_timeliness": avg_timeliness,
                    "timeliness_score": round(employee.timeliness_score or 0.0, 2),
                    "timeliness_result": dict(employee._fields["timeliness_target_result"].selection).get(employee.timeliness_target_result, ""),
                    "avg_responsiveness": round(employee.responsiveness_score or 0.0, 2),
                    "responsiveness_result": dict(employee._fields["responsiveness_target_result"].selection).get(employee.responsiveness_target_result, ""),
                    "avg_punctuality": round(employee.punctuality_score or 0.0, 2),
                    "punctuality_result": dict(employee._fields["punctuality_target_result"].selection).get(employee.punctuality_target_result, ""),
                    "avg_quantity": round(employee.quantity_score or 0.0, 2),
                    "quantity_result": dict(employee._fields["quantity_target_result"].selection).get(employee.quantity_target_result, ""),
                    "avg_quality": round(employee.quality_score or 0.0, 2),
                    "quality_result": dict(employee._fields["quality_target_result"].selection).get(employee.quality_target_result, ""),
                    "avg_effectiveness": round(employee.effectiveness_score or 0.0, 2),
                    "effectiveness_result": dict(employee._fields["effectiveness_target_result"].selection).get(employee.effectiveness_target_result, ""),
                    "avg_efficiency": round(employee.efficiency_score or 0.0, 2),
                    "efficiency_result": dict(employee._fields["efficiency_target_result"].selection).get(employee.efficiency_target_result, ""),
                    "avg_financial_accuracy": round(employee.accuracy_score or 0.0, 2),
                    "accuracy_result": dict(employee._fields["accuracy_target_result"].selection).get(employee.accuracy_target_result, ""),
                    "tasks_completed": employee.tasks_completed,
                    "tasks_on_time": employee.tasks_on_time,
                    "task_target_monthly": employee.task_target_monthly or 0,
                    "messages_response_time": round(employee.messages_response_time or 0.0, 2),
                    "posts_published": employee.posts_published or 0,
                    "total_meetings": employee.total_meetings or 0,
                    "total_lates": employee.total_lates or 0,
                    "total_contract_hours": round(employee.contracted_hours or 0.0, 2),
                    "total_rendered_hours": round(employee.hours_rendered or 0.0, 2),
                    "attendance_rate": attendance_rate,
                    "hours_variance": round(
                        (employee.hours_rendered or 0.0) - (employee.contracted_hours or 0.0), 2
                    ),
                    "metric_targets": self._get_metric_target_map(employee),
                    "timeliness_target_percentage": int(employee.timeliness_target_percentage or 0),
                    "responsiveness_target_percentage": int(employee.responsiveness_target_percentage or 0),
                    "punctuality_target_percentage": int(employee.punctuality_target_percentage or 0),
                    "quantity_target_percentage": int(employee.quantity_target_percentage or 0),
                    "quality_target_percentage": int(employee.quality_target_percentage or 0),
                    "effectiveness_target_percentage": int(employee.effectiveness_target_percentage or 0),
                    "efficiency_target_percentage": int(employee.efficiency_target_percentage or 0),
                    "accuracy_target_percentage": int(employee.accuracy_target_percentage or 0),
                    "meets_score_target": employee.average_score >= employee._target_percentage_to_score(employee.timeliness_target_percentage),
                    "meets_timeliness_target": employee.timeliness_target_result == "success",
                    "overall_target_status": "On Track" if all(
                        metric["result"] == "success" for metric in self._get_metric_target_map(employee)
                    ) else "Needs Attention",
                    "evaluation_count": evaluation_count,
                }
            )

            summary_rows[-1]["metric_analysis"] = [
                self._build_metric_analysis(metric)
                for metric in summary_rows[-1]["metric_targets"]
            ]
            summary_rows[-1]["attention_metrics"] = [
                item for item in summary_rows[-1]["metric_analysis"] if item["result"] != "success"
            ]
            summary_rows[-1]["overall_insight"] = self._build_overall_insight(summary_rows[-1])
            summary_rows[-1]["recommended_target_lines"] = self._build_recommended_target_lines(summary_rows[-1])

        return summary_rows

    def action_generate_csv_report(self):
        validation = self._validate_scope()
        if validation:
            return validation
        evaluations = self._get_evaluations()
        summary_rows = self._get_summary_rows(evaluations)
        selected_columns = self._get_selected_csv_columns()

        if not selected_columns:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Columns Selected",
                    "message": "Please select at least one CSV column to export.",
                    "sticky": False,
                    "type": "warning",
                },
            }

        if not evaluations and not summary_rows:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Data",
                    "message": "No records found for the selected filters.",
                    "sticky": False,
                },
            }

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([label for label, _getter in selected_columns])

        summary_map = {row["employee"].id: row for row in summary_rows}
        if evaluations:
            for evaluation in evaluations:
                row = summary_map.get(evaluation.employee_id.id)
                writer.writerow([getter(evaluation, row) for _label, getter in selected_columns])
        else:
            for row in summary_rows:
                writer.writerow([getter(False, row) for _label, getter in selected_columns])

        filename = self._get_metrics_csv_filename()
        return self._build_csv_download(output.getvalue(), filename)

    def action_generate_summary_report(self):
        validation = self._validate_scope()
        if validation:
            return validation
        summary_rows = self._get_summary_rows()
        selected_columns = self._get_selected_csv_columns()

        if not selected_columns:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Columns Selected",
                    "message": "Please select at least one CSV column to export.",
                    "sticky": False,
                    "type": "warning",
                },
            }

        if not summary_rows:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Data",
                    "message": "No intern KPI records found.",
                    "sticky": False,
                },
            }

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([label for label, _getter in selected_columns])

        for row in summary_rows:
            writer.writerow([getter(False, row) for _label, getter in selected_columns])

        filename = self._get_metrics_csv_filename()
        return self._build_csv_download(output.getvalue(), filename)

    def action_generate_pdf_report(self):
        validation = self._validate_scope()
        if validation:
            return validation
        if not self._get_summary_rows():
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Data",
                    "message": "No intern KPI records found.",
                    "sticky": False,
                },
            }
        return self.env.ref(
            "famtech_intern_dashboard.action_report_hr_kpi_insights"
        ).report_action(self)

    def get_report_payload(self):
        evaluations = self._get_evaluations()
        summary_rows = self._get_summary_rows(evaluations)
        total_evaluations = len(evaluations)
        avg_score = (
            round(sum(row["avg_score"] for row in summary_rows) / len(summary_rows), 2)
            if summary_rows
            else 0.0
        )
        avg_timeliness = (
            round(sum(row["avg_timeliness"] for row in summary_rows) / len(summary_rows), 2)
            if summary_rows
            else 0.0
        )
        avg_responsiveness = (
            round(sum(row["avg_responsiveness"] for row in summary_rows) / len(summary_rows), 2)
            if summary_rows
            else 0.0
        )
        avg_attendance_rate = (
            round(sum(row["attendance_rate"] for row in summary_rows) / len(summary_rows), 2)
            if summary_rows
            else 0.0
        )
        avg_response_time = (
            round(sum(row["messages_response_time"] for row in summary_rows) / len(summary_rows), 2)
            if summary_rows
            else 0.0
        )
        strong_performers = [
            row for row in summary_rows if row["overall_target_status"] == "On Track"
        ]
        attention_needed = [
            row for row in summary_rows if row["overall_target_status"] != "On Track"
        ]
        recommended_targets = summary_rows[0]["metric_analysis"] if len(summary_rows) == 1 else []
        is_single_employee = self.employee_scope == "single" and bool(self.employee_id)
        group_metric_rankings = self._build_group_metric_rankings(summary_rows) if not is_single_employee else []
        return {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "employee_scope": self.employee_scope,
            "employee_name": self.employee_id.name if self.employee_id else "All Employees",
            "summary_rows": summary_rows,
            "total_evaluations": total_evaluations,
            "avg_score": avg_score,
            "avg_timeliness": avg_timeliness,
            "avg_responsiveness": avg_responsiveness,
            "avg_attendance_rate": avg_attendance_rate,
            "avg_response_time": avg_response_time,
            "intern_count": len(summary_rows),
            "strong_performers": strong_performers,
            "attention_needed": attention_needed,
            "strong_performer_count": len(strong_performers),
            "attention_needed_count": len(attention_needed),
            "recommended_targets": recommended_targets,
            "recommended_target_lines": summary_rows[0]["recommended_target_lines"] if len(summary_rows) == 1 else [],
            "group_insights": self._build_group_insights(summary_rows),
            "group_metric_rankings": group_metric_rankings,
            "is_single_employee": is_single_employee,
        }
