from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProjectTask(models.Model):
    """Extends project task to add QA scoring for intern tasks"""

    _inherit = 'project.task'

    qa_score = fields.Float(string="QA Score")
    
    user_ids = fields.Many2many(
        'res.users',
        string='Assignees',
        domain=[] 
    )

    @api.constrains('qa_score')
    def _check_qa_score(self):
        """Ensure QA score is between 1 and 5"""
        for rec in self:
            if rec.qa_score and (rec.qa_score < 1 or rec.qa_score > 5):
                raise ValidationError("QA Score must be between 1 and 5.")
            
    @api.constrains('qa_score', 'state')
    def _check_qa_score_stage(self):
        """Prevent setting QA score on incomplete tasks"""
        for rec in self:
            if rec.qa_score and rec.state != '1_done':
                raise ValidationError("QA Score can only be set when the task is completed.")