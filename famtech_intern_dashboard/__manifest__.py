{
    'name': 'FAMTECH Intern Dashboard',
    'version': '1.0',
    'depends': [
        'hr',
        'hr_attendance',
        'project',
        'mail',
        'website',
        'portal'
    ],
    'data': [
        # 'security/ir.model.access.csv',       
        'views/intern_dashboard_views.xml',  
        # 'views/portal_intern_onboarding.xml', 
        # 'views/res_config_settings_views.xml', 
        # 'data/cron_intern_hours_alert.xml',  
        # 'data/mail_template_intern_hours.xml', 
        # 'data/mail_template_performance_alert.xml',
        # 'data/gamification_badges.xml',
    ],
    'installable': True,
}