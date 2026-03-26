{
    'name': 'FAMTECH Intern Dashboard',
    'version': '1.0',
    'depends': [
        'hr',
        'hr_attendance',
        'hr_holidays', 
        # 'approval',          - for enterprise only
        'hr_expense',
        'project',
        'mail',
        'website',
        'calendar',
        'portal'
    ],
    'data': [
        'security/ir.model.access.csv',       
        'views/meeting_attendance_views.xml',           
        'views/calendar_event_views.xml',              
        'views/intern_dashboard_views.xml',            
        'views/hr_employee_view.xml',
        'views/project_task_view.xml',
        'views/crm_lead_view.xml',
        'data/cron_compute_intern_metrics.xml',
        # 'views/portal_intern_onboarding.xml', 
        # 'views/res_config_settings_views.xml', 
        # 'data/cron_intern_hours_alert.xml',  
        # 'data/mail_template_intern_hours.xml', 
        # 'data/mail_template_performance_alert.xml',
        # 'data/gamification_badges.xml',
    ],
    'installable': True,
}