from mimetypes import guess_type
from os import link, unlink
from os.path import isfile, abspath, normpath, exists
from pecan import abort, conf, expose, override_template, redirect, render, request, response
from webob.exc import status_map
from webob.static import FileIter

from urbaneclient import UrbaneClientDataError, Client as UrbaneClient

from signup.utils import codes, countries, tzlist

import logging

log = logging.getLogger(__name__)

import pecan

try:
    import simplejson as json
except ImportError:
    import json
except:
    raise

# template context helper
def _gen_context_():
    context = dict(conf['branding'])
    if not 'brand_home' in context:
        context['brand_home'] = 'http://www.' + context['brand_domain']
    if conf.get('enable_contact_extra', False):
        context['enable_contact_extra'] = True
        context['contact_extra_required'] = conf.get('contact_extra_required', False)
        context['contact_extra_label'] = conf.get('contact_extra_label', 'Extra')
        context['contact_extra_prompt'] = conf.get('contact_extra_prompt', 'Extra data...')
    context['enable_billing'] = conf.get('enable_billing', True)
    context['codes'] = codes()
    context['countries'] = countries()
    context['timezones'] = tzlist()
    agreements = conf.get('agreements', None)
    if conf.get('enable_agreements', True) and agreements and len(agreements):
        context['agreements'] = {}
        for id in agreements:
            descr = agreements[id].split('@')
            title = descr[0]
            url = descr[1] if len(descr) > 1 else '/brand/doc/' + id + '.html'
            context['agreements'][id] = { 'title': title, 'url': url }
    return context

class RootController(object):

    # return application index page
    @expose(template='index.html')
    def index(self):
        return _gen_context_()


    # show success page
    @expose(template='success.html')
    def success(self):
        return _gen_context_()


    @expose('json')
    def signup(self, *kw):
        # perform signup request
        urbane = UrbaneClient(**conf['keystone'])
        log.info('urbane-after connection')
        try:
            log.info('before account creation')
            urbane.create(**request.POST)
            log.info('after account creation')
        except UrbaneClientDataError as e:
            response.status_code = 400
            return e.errors
        except:
            raise
        return {'success': True}


    # return brand asset if it exists or default instead
    @expose(content_type=None)
    def brand(self, *rest):

        brand_id = conf['branding'].get('brand_id', 'default')

        # return doc
        if request.path.startswith('/brand/doc/'):
            tmpl = normpath(request.path.replace('/brand', conf.app.assets_root + '/' + brand_id))
            if brand_id != 'default' and isfile(tmpl):
                f = open(tmpl)
                response.headers['Content-Type'] = 'text/html'
                response.app_iter = FileIter(f)
                return
            else:
                tmpl = request.path.replace('/brand', '')
                return render(tmpl, _gen_context_())

        # return requested brand asset
        path = normpath(request.path.replace('/brand', conf.app.assets_root + '/' + brand_id))
        if not isfile(path):
            path = request.path.replace('/brand', conf.app.assets_root + '/default/')
        if not isfile(path):
            abort(404)

        f = open(path)
        response.headers['Content-Type'] = guess_type(f.name)
        response.app_iter = FileIter(f)

    @expose('error.html')
    def error(self, status):
        try:
            status = int(status)
        except ValueError:  # pragma: no cover
            status = 500
        message = getattr(status_map.get(status), 'explanation', '')
        return dict(status=status, message=message)
