from pecan import make_app
from pecan.hooks import PecanHook

from urbane.utils import Config

import traceback

# helpers
def setup_app(config):

    # setup defaults
    if not hasattr(config, 'date_format'):
        setattr(config, 'date_format', '%Y-%m-%d')
    if not hasattr( config, 'time_format'):
        setatttr(config, 'time_format', '%H:%M:%S')
    if not hasattr(config, 'datetime_format'):
        setattr(config, 'datetime_format', '%s %s' % (config['date_format'], config['time_format']))

    conf = Config()
    conf.read(config['conf_file'])

    config.update(conf.as_dict())

    app_conf = dict(config.app)

    return make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        **app_conf
    )
