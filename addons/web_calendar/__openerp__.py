{
    'name': 'Web Calendar',
    'category': 'Hidden',
    'description':"""
OpenERP Web Calendar view.
==========================

""",
    'version': '2.0',
    'depends': ['web'],
    'js': [
        'static/lib/dhtmlxScheduler/sources/dhtmlxscheduler.js',
        'static/lib/dhtmlxScheduler/sources/ext/dhtmlxscheduler_dhx_terrace.js',
        'static/lib/dhtmlxScheduler/sources/ext/dhtmlxscheduler_minical.js',
        'static/lib/dhtmlxScheduler/sources/ext/dhtmlxscheduler_limit.js',
        'static/lib/dhtmlxScheduler/sources/ext/dhtmlxscheduler_timeline.js',
        'static/lib/dhtmlxScheduler/sources/ext/dhtmlxscheduler_quick_info.js',
        'static/src/js/calendar.js',
    ],
    'css': [
        #'static/lib/dhtmlxScheduler/codebase/dhtmlxscheduler.css',
        'static/lib/dhtmlxScheduler/codebase/dhtmlxscheduler_dhx_terrace.css',
        #'static/lib/dhtmlxScheduler/codebase/dhtmlxscheduler_glossy.css',
        'static/src/css/web_calendar.css'
    ],
    'qweb' : [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
