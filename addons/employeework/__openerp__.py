{
    'name' : 'Employee Work',
    'author' : 'OpenERP',
    'version' : '1.0',
    'depends': ['hr_timesheet_sheet', 'website'],
    'summary' : 'Module for display employee work',
    'description' : 'Display employee project detail with day and week wise views.',
    'category' : 'Project Management',
    'data' : [
        'static/src/xml/employeework_template.xml',
    ],
    'installable' : True,
}
