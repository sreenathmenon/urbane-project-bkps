# Server Specific Configurations
server = {
    'port': '6996',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'urbane.controllers.root.RootController',
    'modules': ['urbane'],
    #'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/signup/templates',
    'debug': True,
    'errors': {
        #404: '/error/404',
        '__force_dict__': True
    }
}

# Logging
logfile = '/var/log/urbane.log'
logging = {
    'root': {'level': 'INFO', 'handlers': ['console']},
    'loggers': {
        'signup': {'level': 'DEBUG', 'handlers': ['console', 'logfile']},
        'pecan': {'level': 'DEBUG', 'handlers': ['console', 'logfile']},
        'py.warnings': {'handlers': ['console']},
        '__force_dict__': True
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'color'
        },
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': logfile,
            'formatter': 'simple'
        },
        '__force_dict__': True
    },
    'formatters': {
        'simple': {
            'format': ('%(asctime)s %(levelname)-5.5s [%(name)s]'
                       '[%(threadName)s] %(message)s')
        },
        'color': {
            '()': 'pecan.log.ColorFormatter',
            'format': ('%(asctime)s [%(padded_color_levelname)s] [%(name)s]'
                       '[%(threadName)s] %(message)s'),
            '__force_dict__': True
        }
    }
}

# config file path
conf_file = './urbane.conf'

# list of boolean param values, that will be treated as True
true_values = [True, 1, '1', 'true', 'True', 'TRUE', 'yes', 'Yes', 'YES', 'on', 'On', 'ON']
false_values = [False, 0, '0', 'false', 'False', 'FALSE', 'no', 'No', 'NO', 'off', 'Off', 'OFF']

# cdate store format
# WARN: do NOT change after DB initialization
datetime_store_format = '%Y-%m-%d %H:%M:%S'

# Date/Time display/expose formats
#date_format = '%Y-%m-%d'
#time_format = '%H:%M:%S'
#datetime_format = '%s %s' % (date_format, time_format)
date_format = '%Y-%m-%d'
time_format = '%H:%M:%S'
datetime_format = '%s %s' % (date_format, time_format)
