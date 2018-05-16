from pecan import make_app
from utils import Config
from os import mkdir, symlink
from os.path import exists
from shutil import rmtree

def setup_app(config):

    conf = Config()
    conf.read(config.app.config_file)

    config.update(conf.as_dict())

    app_conf = dict(config.app)

    # prepare templates
    brand_id = conf['branding'].get('brand_id', 'default')
    brand_tmpl_path = '%s/%s/templates' % (app_conf['assets_root'], brand_id)
    default_tmpl_path = '%s/default/templates' % app_conf['assets_root']
    template_path = app_conf['template_path']
    #print 'Preparing templates for brand `%s`' % brand_id
    rmtree(template_path, ignore_errors=True)
    mkdir(template_path)
    # handle html templates
    for template_name in ['index.html', 'error.html', 'success.html']:
        template_file = '%s/%s' % (brand_tmpl_path, template_name)
        if exists(template_file):
            symlink(template_file, '%s/%s' % (template_path, template_name))
        else:
            symlink('%s/%s' % (default_tmpl_path, template_name), '%s/%s' % (template_path, template_name))
    # handle doc`s
    if config.get('enable_agreements', True):
        if exists('%s/doc' % brand_tmpl_path):
            symlink('%s/doc' % brand_tmpl_path, '%s/doc' % template_path)
        else:
            symlink('%s/doc' % default_tmpl_path, '%s/doc' % template_path)
        

    return make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        **app_conf
    )
