#
# Urbane signup service
# Copyright: (c) 2016, NephoScale
# Author: Igor V. Dyukov aka div
#

from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mako.template import Template
from pecan import abort, conf, expose, response, request
from pecan.secure import secure
from pecan.rest import RestController
from peewee import *
from pytz import timezone, all_timezones as timezones
from urbane.model import Signup
from urbane.utils import *
from urlparse import urlparse
from webob.exc import HTTPException, HTTPError, HTTPBadRequest, HTTPNotFound

import logging
import operator
import re
import requests as req
import smtplib
import traceback
from keystoneclient import exceptions as client_exceptions

try:
    import simplejson as json
except:
    import json


# determine Keystone API version
auth_url = conf['keystone']['auth_url']
url_path = urlparse(auth_url).path
# TODO(div): Need better Keystone API version matching?
if url_path.startswith('/v2'):
    # use Keystone API v2
    KS_API_V = 2

elif url_path.startswith('/v3'):
    # use Keystone API v3
    KS_API_V = 3

else:
    # unknown KS API version
    raise client_exceptions.ClientException('unable to determine identity API version')

username = conf['keystone']['username']
password = conf['keystone']['password']
tenant = None
domain = None

auth_token = None

admin_tenant_id = None

if KS_API_V == 2:
    tenant = conf['keystone']['tenant']
elif KS_API_V == 3:
    tenant = conf['keystone']['tenant']
    domain = conf['keystone']['domain']

log = logging.getLogger('signup')
log.info(tenant)
log.info(domain)
#
# helper routines
#

# abort request handling with HTTP Bad Request (400) error
def bad_request(message='Invalid request'):
    error = HTTPBadRequest()
    error.explanation = message
    raise error


# import class
def import_class(cname):
    # resolve module and class
    mod = cname.split('.')
    cls = mod.pop()
    mod = '.'.join(mod)
    return getattr(__import__(mod, globals(), locals(), [cls], -1), cls)


# instantiate formatter
def get_formatter(**params):

    # format name
    name = params['format'] if 'format' in params else conf['format']

    # formatter config section name
    fname = 'formatter_' + name

    # formatter config
    fconf = conf[fname] if fname in conf else {}

    # formatter class name
    if isinstance(fconf, dict) and 'class' in fconf:
        cname = fconf.pop('class')
    else:
        cname = name + '.Formatter'

    # instantiate fromatter
    formatter = import_class('urbane.formatters.' + cname)(**fconf)

    # return instance of formatter
    return formatter


# instantiate verifier
def get_verifier(name, **params):

    # verifier config section name
    vname = 'verifier_' + name
    # verifier config
    vconf = conf.get(vname, {})

    # formatter class name
    if isinstance(vconf, dict) and 'class' in vconf:
        cname = vconf.pop('class')
    else:
        cname = name + '.Verifier'

    # instantiate fromatter
    verifier = import_class('urbane.verifiers.' + cname)(**vconf)

    # return instance of formatter
    return verifier


# parameters validation helper
def validate(params, update=False):

    _err_ = {}
    field = None

    error = lambda e: _err_.update({field: e}) and False

    # common validation rules
    if update:
        not_empty = lambda e=None: bool(params[field]) or \
            error(e or 'value should not be empty') if field in params else True

        min_length = lambda l, e=None: (len(params[field]) >= l) or \
            error(e or 'value must be at least ' + str(l) + ' characters long') if field in params else True

        valid = lambda f: f not in _err_  if field in params else True

        match = lambda f, e: params[field] == params[f] or error(e) if field in params else True

        regex = lambda r, e: re.match(r, params[field]) or error(e) if field in params else True

        item_of = lambda l: params[field] in l if field in params else True

    else:
        not_empty = lambda e=None: (field in params and bool(params[field])) or \
            error(e or 'value should not be empty')

        min_length = lambda l, e=None: (len(params[field]) >= l) or \
            error(e or 'value must be at least ' + str(l) + ' characters long')

        valid = lambda f: f not in _err_

        match = lambda f, e: params[field] == params[f] or error(e)

        regex = lambda r, e: re.match(r, params[field]) or error(e)

        item_of = lambda l: params[field] in l


    # perform validation

    field = 'contact_person'
    not_empty()

    # `organization` may be empty for individuals
    #field = 'organization'
    #not_empty()

    field = 'contact_address'
    not_empty()

    field = 'contact_email'
    not_empty() and \
    regex(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', 'value must be a valid email')

    field = 'contact_phone'
    not_empty() and \
    regex(r'^(\((\+?\d{1,3}(\-\d+)?)\)|(\+?\d{1,3}(\-\d+)?))?\s?\d+([\-\.\s]?\d+)*$', 'value must be a valid phone number')

    field = 'contact_timezone'
    not_empty() and item_of(timezones) or error('invalid timezone')


    field = 'username'
    not_empty() and \
    min_length(conf.min_username_length) and \
    regex(r'^[a-zA-Z][a-zA-Z0-9_]+$', 'value must consist of alphanumeric and underscore (_) characters including first letter')

    field = 'password'
    not_empty() and \
    min_length(conf.min_password_length)

    field = 'confirm_password'
    valid('password') and \
    not_empty() and \
    match('password', 'passwords must match')

    #field = 'contact_referral'
    #not_empty()

    if conf.get('enable_billing', True):
        field = 'billing_cc_holder'
        not_empty()

        field = 'billing_cc_number'
        not_empty()

        field = 'billing_cc_expire'
        not_empty() and \
        regex('^\d{1,2}\/\d{2}(\d{2})?$', 'value must be of format mm/yyyy')

        field = 'billing_cc_secret'
        not_empty() and \
        regex('^\d{3,4}$', 'value must a valid credit card verification code')


        field = 'billing_use_contact_address'
        if not (field in params and params[field] in conf.true_values):

            field = 'billing_address'
            not_empty()

    if conf.get('enable_agreements', True):
        field = 'accept_agreement'
        not_empty() and item_of(conf.true_values) or \
            error('aggreement must be accepted')

    return False if len(_err_) == 0 else _err_


# check client region
def check_region():

    region = request.GET.get('region', request.GET.get('region_name', request.POST.get('region', request.POST.get('region_name', 'stage2'))))
    log.info(region)
    log.info(conf.get('region'))
    if conf.get('region', 'RegionOne') != region:
        abort(403)

    return True

# keystone v2 service catalog
v2_service_catalog = None
v3_service_catalog = None

# keystone authorization and policy check
def authenticate():

    global auth_token, username, password, domain, tenant, admin_tenant_id, v2_service_catalog, v3_service_catalog
    log.info('Inside authenticate function')
    check_region()
    log.info('after region checkkkkk')

    # find subject auth token
    log.info('AUTH: checking authorization')
    subject_token = None
    if ('X-Auth-Token' in request.headers):
        log.info('AUTH: found X-Auth-Token')
        subject_token = request.headers['X-Auth-Token'].strip()
    else:
        log.error('AUTH: auth token not found')
        abort(401)

    #print '*** %s ***' % auth_token

    # validate existing auth token
    if auth_token:
        log.info('Validating the auth_token')
        # KS API v2
        if KS_API_V == 2:
            log.info('Entering since version is 2')
            res = req.get(
                auth_url + '/tokens/' + auth_token,
                headers={
                    'X-Auth-Token': auth_token
                }
            )
            if res.status_code not in [200, 203, 204]:
                auth_token = None
                return authenticate()

        # KS API v3
        elif KS_API_V == 3:
            log.info('Entering since version is 3')
            res = req.get(
                auth_url + '/auth/tokens',
                headers={
                    'X-Auth-Token': auth_token,
                    'X-Subject-Token': auth_token
                }
            )
            if res.status_code != 200:
                log.info('error during validation')
                auth_token = None
                return authenticate()

        # ambiguous state
        else:
            return False

    # issue new admin auth token and check roles
    else:
        log.info('Entering the loop to generate a new auth token')
        # KS API v2
        if KS_API_V == 2:
            log.info('entering loop sinc eversion is 2')
            res = req.post(
                auth_url + '/tokens',
                json={
                    'auth': {
                        'tenantName': tenant,
                        'passwordCredentials': {
                            'username': username,
                            'password': password
                        }
                    }
                }
            )
            if res.status_code not in [200, 203]:
                raise client_exceptions.ClientException('unable to issue admin auth token')
            data = json.loads(res.text)
            auth_token = data['access']['token']['id']
            admin_tenant_id = data['access']['token']['tenant']['id']
            v2_service_catalog = data['access']['serviceCatalog']

        # KS API v3
        elif KS_API_V == 3:
            log.info('entering loop since version is 3')
            res = req.post(
                auth_url + '/auth/tokens',
                json={
                    'auth': {
                        'identity': {
                            'methods': [
                                'password'
                            ],
                            'password': {
                                'user': {
                                    'name': username,
                                    'password': password,
                                    'domain': {
                                        'id': domain
                                    }
                                }
                            }
                        },
                        'scope': {
                            'project': {
                                'name': tenant,
                                'domain': {
                                    'id': domain
                                }
                            }
                        }
                    }
                }
            )
            log.info('status code is ')
            log.info(res.status_code)
            log.info(res.headers)

            log.info(res.text)
            log.info('++++++++++++++++++++++++++++')
            data = json.loads(res.text)
            if res.status_code != 201:
                raise client_exceptions.ClientException('unable to issue admin auth token')
            auth_token = res.headers['X-Subject-Token']
            admin_tenant_id    = data['token']['project']['id']
            v3_service_catalog = data['token']['catalog']

            log.info('Got auth token. It is ')
            log.info(auth_token)

        # ambiguous state
        else:
            return False

    user_roles = []
    ''' 

    # validate subject token
    if KS_API_V == 2:
        res = req.get(
            auth_url + '/tokens/' + subject_token,
            headers={
                'X-Auth-Token': auth_token
            }
        )
        if res.status_code not in [200, 203, 204]:
            return False
        data = json.loads(res.text)
        user_roles = data['access']['user']['roles']

    elif KS_API_V == 3:
        log.info('Token validation section')
        log.info(auth_url)
        admin_token = 'RCxbuGsvp8bx'
        res = req.get(auth_url + '/auth/tokens',headers={'X-Auth-Token': admin_token,'X-Subject-Token': auth_token})
        #res = req.get(auth_url + '/auth/tokens',headers={'X-Auth-Token': auth_token})
        log.info(res.status_code)
        log.info(res.text)
        print '++++++++++++++++++++++++++'
        if res.status_code != 200:
            return False
        log.info('Token validated successfully')
        data = json.loads(res.text)
        log.info(data['token']['roles'])
        user_roles = data['token']['roles']

    else:
        log.info('Error!')
        return False

    # check if user has one of allowed roles
    for role in user_roles:
        if role['name'] in conf.allowed_roles:
            return True
    
    return False
    '''
    return True


# render template from `templates` dir
def render_template(name):
    tmpl = Template(filename='%s/%s' % (conf['app']['template_path'], name))
    body = tmpl.render(**conf['branding'])
    return body


# send multipart email
def send_mail(subject=None, sender=None, to=None, body=None, html=None, smtp_host='localhost', smtp_port=25, username=None, password=None):

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ','.join(to) if isinstance(to, list) else to

    # Record the MIME types of both parts - text/plain and text/html.
    if body:
        body_part = MIMEText(body, 'plain')
    if html:
        html_part = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(body_part)
    msg.attach(html_part)

    smtp = smtplib.SMTP(smtp_host, smtp_port)
    smtp.ehlo()
    if username and password:
        smtp.login(username, password)
    smtp.sendmail(sender, to, msg.as_string())
    smtp.quit()


# discover service public endpoint URL
def get_endpoint(service_type):

    region = conf.get('region', 'RegionOne')

    #Case for Keystone V2
    if KS_API_V == 2:
        for service in v2_service_catalog:
            if service['type'] == service_type:
                for endpoint in service['endpoints']:
                    if endpoint['region'] == region:
                        endpoint_url = endpoint.get('publicURL', None)
                        if endpoint_url:
                            return endpoint_url
        return None
    else:
        #Case for Keystone V3
        for service in v3_service_catalog:
            if service['type'] == service_type:
                for endpoint in service['endpoints']:
                    if endpoint['interface'] == 'public':
                        if region:
                            if endpoint['region'] == region:
                                endpoint_url = endpoint['url']
                                return endpoint_url
                                break
                            else:
                                endpoint_url = endpoint['url']
                                return endpoint_url
                                break
        return None


#
# root controller
#
class RootController(RestController):

    #
    # REST API
    #

    # GET /<id>
    # return signup
    @secure(authenticate)
    @expose(content_type='application/json')
    def get_one(self, id, **params):

        # handle helpers
        if id == 'countries':
            return self.countries()

        if id == 'timezones':
            return self.timezones()

        if not authenticate():
            abort(401)

        return self.browse(id=id, **params)


    # GET /
    # return signups
    @secure(authenticate)
    @expose(content_type='application/json')
    def get_all(self, **params):
        log.info('Step 1 - Inside get all')
        return self.browse(**params)


    # POST /
    # create signup
    @secure(check_region)
    @expose(content_type='application/json')
    def post(self, **params):
        log.info('Step - Inside signup creation')
        return self.create(**params)


    # PUT /<id>[/<action>]
    # update signup
    @secure(authenticate)
    @expose(content_type='application/json')
    def put(self, id, action=None, **params):
        if not id:
            return bad_request()

        # perform signup action
        if action:
            if not hasattr(self, action):
                bad_request()
            return getattr(self, action)(id=id, **params)

        return self.update(id, **params)


    # DELETE /<id>
    # remove signup(s)
    @secure(authenticate)
    @expose(content_type='application/json')
    def delete(self, id=None, **params):
        # delete specified signup
        if id:
            params['id'] = id
            if not Signup.erase(**params):
                abort(404)
            response.status = 200
            return '{}'
        # TODO: delete signups by filter

    #
    # API methods
    #

    # browse signup(s)
    def browse(self, id=None, **params):

        log.info('Inside browse function')
        # get dataset
        try:
            result = Signup.fetch(id, **params)
            log.info('Fetch the signup data')
        except AssertionError:
            log.error(traceback.format_exc())
            bad_request()
        except:
            log.error(traceback.format_exc())
            abort(503)

        if id and not result:
            abort(404)

        datum = None
        log.info(type(result))
        if type(result) is Signup:
            datum = result.as_dict(plain=getattr(conf, 'plain_objects', True))
            datum['cdate'] = datetime.strftime(result.cdate, conf.datetime_format)
            # decrypt password
            if params.get('decrypt_password', False):
                datum['password'] = decrypt(conf['database']['cipher_key'], datum['password'])
            # mangle credit card number
            if conf.get('enable_billing', True):
                datum['billing_cc_number'] = format_cc_number(decrypt(conf['database']['cipher_key'], datum['billing_cc_number']), \
                    params.get('cc_number_mangle', True), params.get('cc_number_prefix', True))

        else:
            datum = []

            for signup in result:
                log.info('1111')
                item = signup.as_dict(plain=getattr(conf, 'plain_objects', True))
                item['cdate'] = datetime.strftime(signup.cdate, conf.datetime_format)
                # decrypt password
                item['password'] = decrypt(conf['database']['cipher_key'], item['password'])
                log.info('PASSSSSS')
                log.info(item['password'])
                log.info('2222')
                # mangle credit card number
                if conf.get('enable_billing', True) and (params.get('mangle_cc_number', True)):
                    item['billing_cc_number'] = format_cc_number(decrypt(conf['database']['cipher_key'], item['billing_cc_number']), \
                        params.get('cc_number_mangle', True), params.get('cc_number_prefix', True))
                datum.append(item)
                log.info('33333')

        return get_formatter(**params)(datum, **params)


    # create signup
    def create(self, **params):

        log.info('Inside creation method')
        # id should not exist in params
        if 'id' in params:
            bad_request()

        datum = normalize(params)
        log.info('Normalized data is ')
        log.info(datum)

        # validate params
        errors = validate(datum)

        if errors:
            response.status = 400
            return get_formatter(**datum)(errors, data_root='errors', **datum)

        try:
            # remove unneeded data
            datum.pop('confirm_password', None)
            datum.pop('accept_agreement', None)

            # encrypt password
            datum['password'] = encrypt(conf['database']['cipher_key'], datum['password'])

            # encrypt credit card number
            if conf.get('enable_billing', True):

                datum['billing_cc_number'] = encrypt(conf['database']['cipher_key'], datum['billing_cc_number'])

                # do not store credit card secret (CCV)
                # TODO(div): delayed verification of credit card without storing its CCV???
                datum.pop('billing_cc_secret', None)

                # handle billing_use_contact_address
                if 'billing_use_contact_address' in datum and datum['billing_use_contact_address']:
                    datum.pop('billing_use_contact_address')
                    datum['billing_address'] = datum['contact_address']

            # store signup
            datum['id'] = Signup.store(**datum)

            # start auto-verification
            if conf.signup_auto_verify and conf['verify'] and len(conf['verify']) > 0:
                self.verify(**datum)

        # TODO(div): move into validate()
        # 1st step: checkout own database for username
        # 2nd step: checkout keystone for username(domain???)
        except IntegrityError:
            response.status = 400
            return get_formatter(**datum)({'username': 'provided value could not be used'}, data_root='errors', **datum)

        except:
            log.error(traceback.format_exc())
            abort(500)
            #raise

        return self.browse(**datum)


    # update signup
    def update(self, id, **params):

        datum = normalize(params)

        if len(datum.keys()) <= 0:
            return self.get(id=id)

        if 'password' in datum:
            datum['confirm_password'] = datum['password']

        if conf.get('enable_billing', True) and 'billing_use_contact_address' in datum and datum['billing_use_contact_address']:
            # fetch signup data to copy contact address
            signup = Signup.fetch(id=id)
            if not signup:
                abort(404)
            datum['billing_address'] = signup.contact_address

        # validate params
        errors = validate(datum, update=True)

        if errors:
            response.status = 400
            return get_formatter(**datum)(errors, data_root='errors', **datum)

        # update signup
        try:
            # remove unneeded data
            datum.pop('confirm_password', None)
            datum.pop('accept_agreement', None)

            # encrypt password
            if 'password' in datum:
                datum['password'] = encrypt(conf['database']['cipher_key'], datum['password'])

            # encrypt credit card number
            if conf.get('enable_billing', True) and 'billing_cc_number' in datum and datum['billing_cc_number'][0] != '*':
                datum['billing_cc_number'] = encrypt(conf['database']['cipher_key'], datum['billing_cc_number'])
            # store signup
            Signup.store(id=id, **datum)

        # TODO(div): move to validate()
        # 1st step: checkout own database for username
        # 2nd step: checkout keystone for username(domain???)
        except IntegrityError:
            response.status = 400
            return get_formatter(**datum)({'username': 'provided value could not be used'}, data_root='errors', **datum)

        except:
            log.error(traceback.format_exc())
            abort(500)
            #raise

        return self.browse(id=id, **datum)


    # verify signup(s)
    # TODO: implement async verifiers
    def verify(self, id, **params):

        score = 0

        params['state'] = 'V'
        Signup.store(id=id, **params)

        # TODO: async verification
        if conf['verify']:
            if not isinstance(conf['verify'], list):
                conf['verify'] = [conf['verify']]
            signup = Signup.fetch(id=id, **params)
            if not signup.extra:
                signup.extra = {}
            for name in conf['verify']:
                verify = get_verifier(name, **params)
                try:
                    score += verify(signup)
                except:
                    # set signup into `Failed` state
                    params['state'] = 'F'
                    try:
                        Signup.store(id=id, **params)
                    except:
                        pass
                    log.error(traceback.format_exc())
                    abort(500)
                    #raise

        params['score'] = score
        Signup.store(**signup.as_dict())

        # check if signup auto-accept is allowed and check if score is >= `signup_auto_accept_score`
        # default value for `signup_auto_accept_score` is number of verifiers meaning all verifiers should return at least 1
        if conf.get('signup_auto_accept', False) and score >= conf.get('signup_auto_accept_score', len(conf.get('verify', 0))):
            return self.accept(id, **params)

        # check if signup auto-reject is allowed and check if score is <= `signup_auto_reject_score`
        # default value for `signup_auto_reject_score` is -1
        if conf.get('signup_auto_reject', False) and score <= conf.get('signup_auto_reject_score', -1):
            return self.reject(id, **params)

        # set signup into `Pending` state
        params['state'] = 'P'
        Signup.store(id=id, **params)
        return self.browse(id=id, **params)


    # approve signup(s)
    def accept(self, id, **params):
        return self.deploy(id=id, **params)


    # deploy signup(s)
    def deploy(self, id=None, signup=None, **params):
        global v2_service_catalog

        log.info('ID is ')
        log.info(id)
        if not type(signup) is Signup:
            log.info('loop1')
            if id:
                log.info('looop2')
                signup = Signup.fetch(id=id)
                log.info(signup)
            else:
                abort(400)

        if not authenticate():
            abort(401)

        if conf.get('enable_billing', True):
            address = signup.billing_address.split(', ')
            cc_number = decrypt(conf['database']['cipher_key'], signup.billing_cc_number)
        else:
            print 'CONTACTTTTT ADDRESSSSS'
            print signup
            print type(signup)
            print signup.__dict__
            print signup.contact_address
            print '++++++++++++++++++++++++'
            address = signup.contact_address.split(', ')
            cc_number = 'N/A'
        address_country = address.pop()
        address_zip = address.pop()
        address_state = address.pop()
        address_city = address.pop()
        address_street = ", ".join(address)

	(last_name, first_name) = signup.contact_person.split(', ')

        if KS_API_V == 2:
            tenant = {
                'name': signup.username,
                'description': signup.billing_cc_holder,
                'enabled': True,
                'address_street': address_street,
                'address_city': address_city,
                'address_state': address_state,
                'address_zip': address_zip,
                'address_country': address_country,
                'creation_date': datetime.now().strftime(conf.datetime_format),
                'signup_date': signup.cdate.strftime(conf.datetime_format)
            }
            if conf.get('enable_billing', True):
                tenant.update({
                    'billing_balance': 0,
                    'billing_cc_holder': signup.billing_cc_holder,
                    'billing_cc_type': get_cc_type(cc_number),
                    'billing_cc_number': encrypt(conf['database']['cipher_key'], cc_number),
                    'billing_cc_expire': signup.billing_cc_expire
                })
            # create tenant
            url = auth_url + '/tenants'
            try:
                res = req.post(
                    url,
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'tenant': tenant
                    }
                )
                print auth_url + '/tenants', res.text
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant')
                    abort(500)
                tenant = json.loads(res.text)['tenant']
            except:
                log.error(traceback.format_exc())
                abort(500)

            # create user
            try:
                res = req.post(
                    auth_url + '/users',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'user': {
                            'username': signup.username,
                            'name': signup.username,
                            'password': decrypt(conf['database']['cipher_key'], signup.password),
                            'email': signup.contact_email,
                            'tenantId': tenant['id'],
                            'enabled': True,
                            'first_name': first_name,
                            'last_name': last_name,
                            'phone_num': signup.contact_phone
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant user')
                    abort(500)
            except:
                log.error(traceback.format_exc())
                abort(500)

            #
            # apply Nova (compute) quotas
            #

            quotas = conf.get('deploy_nova_quotas', None)
            if quotas:
                # prepare nova public endpoint URL
                endpoint_url = get_endpoint('compute')
                if not endpoint_url:
                    log.error('FATAL: unable to discover compute service (Nova) public endpoint URL')
                    abort(500)
                endpoint_url = endpoint_url.replace('%(tenant_id)s', admin_tenant_id) + '/os-quota-sets/' + tenant['id']
                try:
                    res = req.put(
                        endpoint_url,
                        headers={
                            'X-Auth-Token': auth_token
                        },
                        json={
                            'quota_set': quotas
                        }
                    )
                    if res.status_code != 200:
                        log.error('FATAL: unable to apply compute service quotas')
                        abort(500)
                except:
                    log.error(traceback.format_exc())
                    abort(500)
            else:
                log.warning('Compute service (Nova) quotas are not configured')

            #
            # apply Neutron (network) quotas
            #

            # prepare neutron public endpoint URL
            endpoint_url = get_endpoint('network')
            if not endpoint_url:
                log.error('FATAL: unable to discover network service (Neutron) public endpoint URL')
                abort(500)
            endpoint_url = endpoint_url + '/v2.0/'
            try:
                quotas = conf.get('deploy_neutron_quotas', None)
                if quotas:
                    res = req.put(
                        endpoint_url + 'quotas/' + tenant['id'],
                        headers={
                            'X-Auth-Token': auth_token
                        },
                        json = {
                            'quota': quotas
                        }
                    )
                    if res.status_code != 200:
                        log.error('FATAL: unable to apply project/tenant network quotas')
                        abort(500)

                else:
                    log.warning('Network service (Neutron) quotas are not configured')

            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant network quotas has been applied.')

            #
            # Apply Cinder (block-storage) quotas
            #
            quotas = conf.get('deploy_cinder_quotas', None)
            if quotas:

                # prepare nova public endpoint URL
                endpoint_url = get_endpoint('volumev2')
                if not endpoint_url:
                    log.error('FATAL: unable to discover block-storage service (Cinder) public endpoint URL')
                    abort(500)
                endpoint_url = endpoint_url.replace('%(tenant_id)s', admin_tenant_id) + '/os-quota-sets/' + tenant['id']
                try:
                    res = req.put(
                        endpoint_url,
                        headers={
                            'X-Auth-Token': auth_token
                        },
                        json={
                            'quota_set': quotas
                        }
                    )
                    if res.status_code != 200:
                        log.error('FATAL: unable to apply block-storage service quotas')
                        abort(500)
                except:
                    log.error(traceback.format_exc())
                    abort(500)

            else:
                log.warning('Block-storage service (Cinder) quotas are not configured')

            #
            # Create routers & networks
            #

            # prepare neutron public endpoint URL
            endpoint_url = get_endpoint('network')
            if not endpoint_url:
                log.error('FATAL: unable to discover network service (Neutron) public endpoint URL')
                abort(500)
            endpoint_url = endpoint_url + '/v2.0/'

            # *** create project router ***

            # get external network
            ext_network = None
            try:
                res = req.get(
                    endpoint_url + 'networks.json',
                    params={
                        'name': conf['deploy_neutron'].get('external_network', 'public')
                    },
                    headers={
                        'X-Auth-Token': auth_token
                    }
                )
                if res.status_code != 200:
                    log.error('FATAL: unable to discover external network')
                    abort(500)

                ext_network = json.loads(res.text)['networks'][0]
            except:
                log.error(traceback.format_exc())
                abort(500)
            if not ext_network:
                log.error('FATAL: external network not found')
                abort(500)

            router_name = conf['deploy_neutron'].get('router_name_format', '${tenant_name}-gw')
            router_name = router_name.replace('${tenant_id}', tenant['id']).replace('${tenant_name}', tenant['name'])
            # do create router request
            try:
                res = req.post(
                    endpoint_url + 'routers.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'router': {
                            'tenant_id': tenant['id'],
                            'name': router_name,
                            'external_gateway_info': {
                                'network_id': ext_network['id']
                            }
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant router')
                    abort(500)
                router = json.loads(res.text)['router']
            except:
                log.error(traceback.format_exc())
                abort(500)

            if not router:
                log.error('FATAL: unable to create project/tenant router')
                abort(500)

            log.info('Project/tenant router has been created.')

            # *** create project/tenant internal network ***

            int_network = None
            network_name = conf['deploy_neutron'].get('network_name_format', '${tenant_name}-nw')
            network_name = network_name.replace('${tenant_id}', tenant['id']).replace('${tenant_name}', tenant['name'])
            # do create network request
            try:
                res = req.post(
                    endpoint_url + 'networks.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'network': {
                            'tenant_id': tenant['id'],
                            'name': network_name,
                            'admin_state_up': True
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant internal network')
                    abort(500)
                print res.text
                int_network = json.loads(res.text)['network']
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant network has been created')

            # do create subnet request
            try:
                res = req.post(
                    endpoint_url + 'subnets.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'subnet': {
                            'tenant_id': tenant['id'],
                            'name': 'internal',
                            'network_id': int_network['id'],
                            'ip_version': 4,
                            'cidr': conf['deploy_neutron'].get('internal_network_cidr', '10.0.0.0/24')
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant internal network subnet')
                    abort(500)
                int_subnet = json.loads(res.text)['subnet']
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant subnet has been created.')
            print int_subnet

            # apply internal network to router
            try:
                res = req.put(
                    endpoint_url + 'routers/' + router['id'] + '/add_router_interface.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'tenant_id': tenant['id'],
                        'subnet_id': int_subnet['id']
                    }
                )
                print res.text
                if res.status_code != 200:
                    log.error('FATAL: unable to apply project/tenant internal network subnet')
                    abort(500)
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant subnet has been applied.')



        elif KS_API_V == 3:
            # TODO:
            # create project under configured domain
            # create user
            #raise Exception('Not implemented')

            # TODO:
            # create project under configured domain
            # create user

            #Initializing
            user_domain_id = None
            user_domain    = signup.domain
            log.info('user_domain is ')
            log.info(user_domain)
            log.info('++++++++++++++++++++++++++++++')
           
            log.info('V3 Deployment SECTION STARTS HERREEE')

            #Display error if domain name is not present
            if not user_domain:
                log.error('FATAL: Unable to accept the signup since domain is not present')
                abort(500)

            #Get the domain list and find the id corresponding to the domain name entered by user
            try:
                res = req.get(
                    auth_url + '/domains',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                )
                log.info('+++++++++++++++++++++')
                log.info(res.status_code)
                log.info(res.text)
                domains = json.loads(res.text)['domains']
                log.info(domains)
                log.info('+++++++++++++++++++++')
            except:
                log.error('FATAL: unable to Fetch domain list')
                abort(500)

            for k in domains:

                domain_name = k.get('name', None)
                domain_id   = k.get('id', None)

                print '++++++++++++++++++++++++++++'
                print domain_name
                print domain_id
                print '+++++++++++++++++++++++++++++'

                if domain_id == user_domain:
                    log.info('Already domain id is getting passed!')
                    user_domain_id = user_domain
                    
                if domain_name.lower() == user_domain.lower():
                    log.info('Domain name matches with the values passed from signup!')
                    user_domain_id = k.get('id', None)
                    log.info(user_domain_id)

            if not user_domain_id:
                log.error('FATAL: Unable to accept the signup since domain details are incorrect!')
                abort(500)

            log.info('Fetching of domain id is successful.')

            #TODO - Need to fetch the value of domain name/id and save it in DB
            project = {
                'name'            : signup.username,
                'description'     : signup.billing_cc_holder,
                'enabled'         : True,
                'address_street'  : address_street,
                'address_city'    : address_city,
                'address_state'   : address_state,
                'address_zip'     : address_zip,
                'address_country' : address_country,
                'creation_date'   : datetime.now().strftime(conf.datetime_format),
                'signup_date'     : signup.cdate.strftime(conf.datetime_format),
                'domain_id'       : user_domain_id
            }

            if conf.get('enable_billing', True):
                project.update({
                    'billing_balance'   : 0,
                    'billing_cc_holder' : signup.billing_cc_holder,
                    'billing_cc_type'   : get_cc_type(cc_number),
                    'billing_cc_number' : encrypt(conf['database']['cipher_key'], cc_number),
                    'billing_cc_expire' : signup.billing_cc_expire
                })

            url = auth_url + '/projects'

            try:
                res = req.post(
                    url,
                    headers={
                        'X-Auth-Token': auth_token,
                        'X-Subject-Token': auth_token
                    },
                    json={
                        'project': project
                    }
                )
               
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant')
                    abort(500)

                log.info(res.text)
                project = json.loads(res.text)['project']
            except:
                log.error(traceback.format_exc())
                abort(500)

            log.info('Tenant Creation is successful.')
            log.info(project['id'])

            # create user
            log.info('Going to create user')
            try:
                res = req.post(
                    auth_url + '/users',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'user': {
                            'username': signup.username + str('test'),
                            'name': signup.username,
                            'password': decrypt(conf['database']['cipher_key'], signup.password),
                            'email': signup.contact_email,
                            'default_project_id ': project['id'],
                            'enabled': True,
                            'first_name': first_name,
                            'last_name': last_name,
                            'phone_num': signup.contact_phone,
                            'domain_id': user_domain_id
                        }
                    }
                )

                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create user')
                    abort(500)
                user = json.loads(res.text)['user']
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('User creation is successful')

            #Assign specific roles to user
            #TODO - Need to replace role id section and fetch it directly via api or from config
            try:
                endpoint_url = "/projects/%s/users/%s/roles/7274d9f61e564563924770957021856f" % (project['id'], user['id'])
                
                res = req.put(
                    auth_url + endpoint_url,
                    headers={
                        'X-Auth-Token': auth_token
                    },
                )

                if res.status_code not in [200, 201, 204]:
                    log.error('FATAL: unable to do the rating assignment for newly created user')
                    abort(500)
            except:
               log.error(traceback.format_exc())
               abort(500)
            log.info('Role assignment is successful')

            #
            # apply Nova (compute) quotas
            #
            log.info('Going to apply nova quotas')
            quotas = conf.get('deploy_nova_quotas', None)
            if quotas:

                # prepare nova public endpoint URL
                endpoint_url = get_endpoint('compute')
                if not endpoint_url:
                    log.error('FATAL: unable to discover compute service (Nova) public endpoint URL')
                    abort(500)
                endpoint_url = endpoint_url.replace('%(tenant_id)s', admin_tenant_id) + '/os-quota-sets/' + project['id']
                try:
                    res = req.put(
                        endpoint_url,
                        headers={
                            'X-Auth-Token': auth_token
                        },
                        json={
                            'quota_set': quotas
                        }
                    )

                    if res.status_code != 200:
                        log.error('FATAL: unable to apply compute service quotas')
                        abort(500)
                except:
                    log.error(traceback.format_exc())
                    abort(500)
            else:
                log.warning('Compute service (Nova) quotas are not configured')
            log.info('Compute service (Nova) quotas have been configured.')

            #
            # apply Neutron (network) quotas
            #

            # prepare neutron public endpoint URL
            log.info('Going to apply network quotas')
            endpoint_url = get_endpoint('network')
            if not endpoint_url:
                log.error('FATAL: unable to discover network service (Neutron) public endpoint URL')
                abort(500)
            endpoint_url = endpoint_url + '/v2.0/'
            try:
                quotas = conf.get('deploy_neutron_quotas', None)
                if quotas:
                    res = req.put(
                        endpoint_url + 'quotas/' + project['id'],
                        headers={
                            'X-Auth-Token': auth_token
                        },
                        json = {
                            'quota': quotas
                        }
                    )
                    if res.status_code != 200:
                        log.error('FATAL: unable to apply project/tenant network quotas')
                        abort(500)

                else:
                    log.warning('Network service (Neutron) quotas are not configured')

            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant network quotas has been applied.')

            #
            # Apply Cinder (block-storage) quotas
            #
            log.info('Deploy cinder quotas')
            quotas = conf.get('deploy_cinder_quotas', None)
            if quotas:

                # prepare nova public endpoint URL
                endpoint_url = get_endpoint('volumev2')
                if not endpoint_url:
                    log.error('FATAL: unable to discover block-storage service (Cinder) public endpoint URL')
                    abort(500)
                endpoint_url = endpoint_url.replace('%(tenant_id)s', admin_tenant_id) + '/os-quota-sets/' + project['id']
                try:
                    res = req.put(
                        endpoint_url,
                        headers={
                            'X-Auth-Token': auth_token
                        },
                        json={
                            'quota_set': quotas
                        }
                    )
                    if res.status_code != 200:
                        log.error('FATAL: unable to apply block-storage service quotas')
                        abort(500)
                except:
                    log.error(traceback.format_exc())
                    abort(500)

            else:
                log.warning('Block-storage service (Cinder) quotas are not configured')
            log.info('Cinder quotas have been configured')

            #
            # Create routers & networks
            #

            # prepare neutron public endpoint URL
            endpoint_url = get_endpoint('network')
            if not endpoint_url:
                log.error('FATAL: unable to discover network service (Neutron) public endpoint URL')
                abort(500)
            endpoint_url = endpoint_url + '/v2.0/'

            # *** create project router ***

            # get external network
            ext_network = None
            try:
                res = req.get(
                    endpoint_url + 'networks.json',
                    params={
                        'name': conf['deploy_neutron'].get('external_network', 'public')
                    },
                    headers={
                        'X-Auth-Token': auth_token
                    }
                )
                if res.status_code != 200:
                    log.error('FATAL: unable to discover external network')
                    abort(500)

                ext_network = json.loads(res.text)['networks'][0]
            except:
                log.error(traceback.format_exc())
                abort(500)

            if not ext_network:
                log.error('FATAL: external network not found')
                abort(500)
            log.info('External network configuration has been succesful.')

            router_name = conf['deploy_neutron'].get('router_name_format', '${tenant_name}-gw')
            router_name = router_name.replace('${tenant_id}', project['id']).replace('${tenant_name}', project['name'])
            # do create router request
            try:
                res = req.post(
                    endpoint_url + 'routers.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'router': {
                            'tenant_id': project['id'],
                            'name': router_name,
                            'external_gateway_info': {
                                'network_id': ext_network['id']
                            }
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant router')
                    abort(500)
                router = json.loads(res.text)['router']
            except:
                log.error(traceback.format_exc())
                abort(500)

            if not router:
                log.error('FATAL: unable to create project/tenant router')
                abort(500)
            log.info('Project/tenant router has been created.')

            # *** create project/tenant internal network ***

            int_network = None
            network_name = conf['deploy_neutron'].get('network_name_format', '${tenant_name}-nw')
            network_name = network_name.replace('${tenant_id}', project['id']).replace('${tenant_name}', project['name'])
            # do create network request
            try:
                res = req.post(
                    endpoint_url + 'networks.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'network': {
                            'tenant_id': project['id'],
                            'name': network_name,
                            'admin_state_up': True
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant internal network')
                    abort(500)
                print res.text
                int_network = json.loads(res.text)['network']
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant network has been created')

            # do create subnet request
            try:
                res = req.post(
                    endpoint_url + 'subnets.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'subnet': {
                            'tenant_id': project['id'],
                            'name': 'internal',
                            'network_id': int_network['id'],
                            'ip_version': 4,
                            'cidr': conf['deploy_neutron'].get('internal_network_cidr', '10.0.0.0/24')
                        }
                    }
                )
                if res.status_code not in [200, 201]:
                    log.error('FATAL: unable to create project/tenant internal network subnet')
                    abort(500)
                int_subnet = json.loads(res.text)['subnet']
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant internal network subnet has been created.')

            # apply internal network to router
            try:
                res = req.put(
                    endpoint_url + 'routers/' + router['id'] + '/add_router_interface.json',
                    headers={
                        'X-Auth-Token': auth_token
                    },
                    json={
                        'tenant_id': project['id'],
                        'subnet_id': int_subnet['id']
                    }
                )
                
                if res.status_code != 200:
                    log.error('FATAL: unable to apply internal network to router')
                    abort(500)
            except:
                log.error(traceback.format_exc())
                abort(500)
            log.info('Project/tenant internal network has been applied to router (Interface).')
        else:
            # should never reach here
            abort(400)


        #
        # finalize deployment
        #

        # set signup into `Accepted` state
        params['state'] = 'A'
        Signup.store(id=id, **params)

        # send welcome email
	try:
            send_mail(
                to=[signup.contact_email],
                body=render_template('welcome_email.text'),
                html=render_template('welcome_email.html'),
                **conf['email']
            )
        except:
            log.error('Was unable to send welcome email')
            log.debug(traceback.format_exc())
            pass

        return self.browse(id=id, **params)

    # reject signup(s)
    def reject(self, id, **params):
        # TODO(div): perform reject actions
        params['state'] = 'R'
        Signup.store(id=id, **params)
        return self.browse(id=id, **params)


    # expire signup(s)
    def expire(self, id, **params):
        # TODO(div): perform expire actions
        params['state'] = 'X'
        Signup.store(id=id, **params)
        return self.browse(id=id, **params)

    #
    # helper endpoints
    #

    # return list of known timezones (helper function)
    @expose(content_type='application/json')
    def countries(self, **kwargs):
        data = {}
        for code, item in countries.iteritems():
            data[code] = item['name']
        # order by country name
        data = OrderedDict(sorted(data.items(), key=operator.itemgetter(1)))
        return get_formatter(**kwargs)(data, data_root='countries', **kwargs)


    # return list of known timezones (helper function)
    @expose(content_type='application/json')
    def timezones(self, **kwargs):
        tzlist = OrderedDict()
        for tzname in timezones:
            tz = timezone(tzname)
            tzlist[tzname] = '(GMT%s) %s' % (datetime.now(tz).strftime('%z'), tzname)
        return get_formatter(**kwargs)(tzlist, data_root='timezones', **kwargs)
