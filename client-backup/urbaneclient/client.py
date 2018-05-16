#
# Urbane signup service client
# Copyright: (c) 2016, NephoScale
# Author: Igor V. Dyukov aka div
#

from inspect import getmembers, isroutine
from urlparse import urlparse
try:
    import simplejson as json
except:
    import json
import requests as req

#
# Urbane client errors
#
class UrbaneClientError(Exception):

    message = None

    def __init__(self, *args, **kwargs):
        if self.message:
            super(UrbaneClientError, self).__init__(self.message)
        else:
            super(UrbaneClientError, self).__init__(*args, **kwargs)


class UrbaneClientAuthError(UrbaneClientError):
    message = 'authentication failed'

class UrbaneClientDataError(UrbaneClientError):
    message = 'data error'
    errors = {}

    def __init__(self, errors, *args, **kwargs):
        self.errors = errors
        super(UrbaneClientDataError, self).__init__(*args, **kwargs)


# signup representation class
class Signup(object):

    # id
    id = None
    # create date
    cdate = None
    # account username
    username = None
    # account password
    password = None
    # state
    state = None
    # extra data
    extra = None
    # datum
    datum = {}

    # constructor
    def __init__(self, **kwargs):
        super(Signup, self).__init__()
        # handle `datum`
        datum = kwargs.copy()
        for f in Signup._fields_:
            v = datum.pop(f, None)
            if v: setattr(self, f, v)
        self.datum = datum

    # proxy access to `datum` fields
    def __getattr__(self, f):
        if f[0] == '_' or f in Signup._fields_:
            return super(Signup, self).__getattr__(f)
        else:
            return self.datum.get(f, None)

    def __setattr__(self, f, v):
        if f[0] == '_' or f in Signup._fields_:
            super(Signup, self).__setattr__(f, v)
        else:
            self.datum[f] = v

    def __delattr__(self, f):
        if f[0] == '_' or f in Signup._fields_:
            super(Signup, self).__delattr__(f, v)
        else:
            del self.datum[f]

    # convert signup instance into dict
    def as_dict(self, plain=True):
        _dict_ = dict([(f, getattr(self, f)) for f in Signup._fields_])
        if plain:
            _dict_.update(_dict_.pop('datum'))
        return _dict_

# for internal use
setattr(Signup, '_fields_', filter(lambda f: f[0] != '_', [field[0] for field in getmembers(Signup, lambda m: not isroutine(m))]))

#
# Urbane signup service client class
#
class Client(object):

    # @param {str} auth_url - keystone auth url
    # @param {str} username - username to use for authentication
    # @param {str} password - password to use for authentication
    # @param {str} project - project name to use in keystone session (for keystone API v2)
    # @param {str} [tenant] - alias for project
    # @param {str} [domain] - domain name to use in keystone session (for keystone API v3)
    # TODO:
    # @param {str} project_id - project id to use in keystone session (for keystone API v2)
    # @param {str} tenant_id - alias for project_id
    # @param {str} domain_id - domain id to use in keystone session (for keystone API v3)
    # @param {str} service_url - signup service endpoint (no discovery)
    def __init__(self, **kwargs):
        self._auth_url_ = kwargs.get('auth_url', None)
        self._username_ = kwargs.get('username', None)
        self._password_ = kwargs.get('password', None)
        self._region_ = kwargs.get('region', 'RegionOne')

        # validate common params
        if not self._auth_url_:
            raise UrbaneClientError('parameter auth_url is mandatory')
        if not self._username_:
            raise UrbaneClientError('parameter username is mandatory')
        if not self._password_:
            raise UrbaneClientError('parameter password is mandatory')

        # determine Keystone API version and perform specific actions
        url_path = urlparse(self._auth_url_).path
        # TODO(div): Need better Keystone API version matching?
        if url_path.startswith('/v2'):
            # use Keystone API v2
            self._ks_api_v_ = 2
            # TODO: add support for tenant_id
            self._tenant_ = kwargs.get('project', kwargs.get('tenant', None))
            if not self._tenant_:
                raise UrbaneClientError('parameter project/tenant is mandatory')

        elif url_path.startswith('/v3'):
            # use Keystone API v3
            self._ks_api_v_ = 3
            # TODO: add support for user_domain_id, 'project_domain_name' and 'project_domain_id'
            self._domain_ = kwargs.get('domain', None)
            self._tenant_ = kwargs.get('project', kwargs.get('tenant', None))
            if not self._domain_:
                raise UrbaneClientError('parameter domain is mandatory')

        else:
            # unknown KS API version
            raise UrbaneClientError('unable to determine keystone API version')

        # authenticate & discover signup service URL
        self.authenticate()


    # issue new or validate existing auth token with Keystone,
    # discover signup service public endpoint
    def authenticate(self):

        if getattr(self, '_auth_token_', None):
            #
            # validate token
            #
            if self._ks_api_v_ == 2:
                res = req.post(
                    self._auth_url_ + '/tokens',
                    json={
                        'auth': {
                            'tenantName': self._tenant_,
                            'token': {
                                "id": self._auth_token_
                            }
                        }
                    },
                    headers={
                        'X-Auth-Token': self._auth_token_
                    }
                )
                if res.status_code not in [200, 203]:
                    # re-issue new auth token
                    self._auth_token_ = None
                    return self.authenticate()

            elif self._ks_api_v_ == 3:
                res = req.get(
                    self._auth_url_ + '/auth/tokens',
                    headers={
                        'X-Auth-Token': self._auth_token_,
                        'X-Subject-Token': self._auth_token_
                    }
                )
                if res.status_code != 200:
                    self._auth_token_ = None
                    return self.authenticate()

            else:
                raise UrbaneClientError('ambiguous client state')


        else:
            #
            # issue new token
            #
            # KS API v2
            if self._ks_api_v_ == 2:

                # perform KS request
                res = req.post(
                    self._auth_url_ + '/tokens',
                    json={
                        'auth': {
                            'tenantName': self._tenant_,
                            'passwordCredentials': {
                                'username': self._username_,
                                'password': self._password_
                            }
                        }
                    }
                )
                if res.status_code not in [200, 203]:
                    raise UrbaneClientAuthError()

                data = json.loads(res.text)

                self._auth_token_ = data['access']['token']['id']

                # discover signup service public URL
                # TODO(div): add support for regions
                self._service_url_ = None
                try:
                    service_list = data['access']['serviceCatalog']
                    for service in service_list:
                        if service['type'] == 'signup':
                            self._service_url_ = service['endpoints'][0]['publicURL']
                            break
                except:
                    raise UrbaneClientError('error on discover signup service public URL')
                if not self._service_url_:
                    raise UrbaneClientError('signup service public URL not found')

            # KS API v3
            elif self._ks_api_v_ == 3:
                print self._username_
                print self._password_
                print self._domain_
                # TODO(div): implement v3 issue new auth token
                res = req.post(
                    self._auth_url_ + '/auth/tokens',
                    json={
                        "auth": {
                            "identity": {
                                "methods": [
                                    "password"
                                ],
                                "password": {
                                    "user": {
                                        "name": self._username_,
                                        "password": self._password_,
                                        "domain": {
                                            "id": self._domain_
                                        }
                                    }
                                }
                            },
                            "scope": {
                                "domain": {
                                    "id": self._domain_
                            }
                        }

                        }
                    }
                )
                print res.text
                print res.status_code
                if res.status_code != 201:
                    raise UrbaneClientAuthError()
                self._auth_token_ = res.headers['X-Subject-Token']

                # discover signup service public URL
                # TODO(div): add support for regions
                self._service_url_ = None
                data = json.loads(res.text)
                try:
                    service_list = data['token']['catalog']
                    for service in service_list:
                        if service['type'] == 'signup':
                            for endpoint in service['endpoints']:
                                if endpoint['interface'] == 'public':
                                    if self._region_:
                                        if endpoint['region'] == self._region_:
                                            self._service_url_ = endpoint['url']
                                            break
                                    else:
                                        self._service_url_ = endpoint['url']
                                        break
                        if self._service_url_:
                            break
                except:
                    raise UrbaneClientError('error on discover signup service public URL')
                if not self._service_url_:
                    raise UrbaneClientError('signup service public URL not found')

            else:
                raise UrbaneClientError('ambiguous client state')

            print self._service_url_
            return True

    # create new signup
    def create(self, **kwargs):

        self.authenticate()

        params = kwargs.pop('params', {'format': 'common'})

        if not params.get('region', None):
            params['region'] = self._region_

        res = req.post(
            self._service_url_,
            json=kwargs,
            params=params,
            headers={
                'X-Auth-Token': self._auth_token_
            }
        )
        #print res.text
        if res.status_code == 200:
            data = json.loads(res.text)
            return Signup(**data)
        elif res.status_code == 400:
            raise UrbaneClientDataError(json.loads(res.text)['errors'])
        elif res.status_code in [401, 403]:
            raise UrbaneClientAuthError()
        else:
            raise UrbaneClientError('unable to create signup')


    # update existing signup
    def update(self, kwargs):
        id = kwargs['id']
        if not id:
            raise UrbaneClientError('parameter `id` is mandatory')

        self.authenticate()
        params = kwargs.get('params', {})

        if not params.get('region', None):
            params['region'] = self._region_

        res = req.put(
            self._service_url_ + '/' + str(id),
            json=kwargs,
            params=params,
            headers={
                'X-Auth-Token': self._auth_token_
            }
        )
        # print res.text
        if res.status_code == 200:
            data = json.loads(res.text)
            return Signup(**data)
        elif res.status_code == 400:
            raise UrbaneClientDataError(json.loads(res.text)['errors'])
        elif res.status_code in [401, 403]:
            raise UrbaneClientAuthError()
        elif res.status_code == 404:
            raise UrbaneClientError('requested signup not found')
        else:
            raise UrbaneClientError('unable to update signup')


    # delete specific signup or list of filtered signups
    # TODO(div): implement delete by filter
    def delete(self, id=None, **kwargs):

        if not id:
            raise UrbaneClientError('parameter `id` is mandatory')

        self.authenticate()
        params = kwargs.get('params', {})
        if not params.get('region', None):
            params['region'] = self._region_

        res = req.delete(
            self._service_url_ + '/' + str(id),
            json=kwargs,
            params=params,
            headers={
                'X-Auth-Token': self._auth_token_
            }
        )
        #print res.text
        if res.status_code == 200:
            return True
        elif res.status_code in [401, 403]:
            raise UrbaneClientAuthError()
        elif res.status_code == 404:
            raise UrbaneClientError('requested signup not found')
        else:
            raise UrbaneClientError('unable to delete signup')


    # return list of (filtered) signups
    def list(self, **kwargs):

        #print 'before authentication'
        self.authenticate()
        #print 'after authentication'
        #print self._auth_token_

        kwargs['format'] = 'openstack'
        kwargs['total'] = 'total'

        if not kwargs.get('region', None):
            kwargs['region'] = self._region_

        res = req.get(
            self._service_url_,
            params=kwargs,
            headers={
                'X-Auth-Token': self._auth_token_
            }
        )
        #print res
        #print res.status_code
        #print res.text
        if res.status_code == 200:
            data = json.loads(res.text)
            print  '+++++++++++++++++++++++++>><<<<<<++++++++++++++'
            print  '+++++++++++++++++++++++++>><<<<<<++++++++++++++'
            return [Signup(**item) for item in data['signups']], data['total']
        elif res.status_code in [401, 403]:
            raise UrbaneClientAuthError()
        else:
            raise UrbaneClientError('unable to list signups')


    # return specific signup datum
    def get(self, id=None, **kwargs):

        if not id:
            raise UrbaneClientError('parameter `id` is mandatory')

        self.authenticate()

        kwargs['format'] = 'common'
        if not kwargs.get('region', None):
            kwargs['region'] = self._region_

        res = req.get(
            self._service_url_ + '/' + str(id),
            params=kwargs,
            headers={
                'X-Auth-Token': self._auth_token_
            }
        )
        #print res.text
        if res.status_code == 200:
            data = json.loads(res.text)
            return Signup(**data)
        elif res.status_code in [401, 403]:
            raise UrbaneClientAuthError()
        elif res.status_code == 404:
            raise UrbaneClientError('requested signup not found')
        else:
            raise UrbaneClientError('unable to get signup')

    # approve signup
    # TODO(div): implement approve by filter
    def action(self, id=None, action=None, **kwargs):

        if not id:
            raise UrbaneClientError('parameter `id` is mandatory')

        if not action:
            raise UrbaneClientError('parameter `id` is mandatory')

        self.authenticate()
        params = kwargs.get('params', {})
        if not params.get('region', None):
            params['region'] = self._region_

        res = req.put(
            '%s/%s/%s' % (self._service_url_, str(id), action),
            params=params,
            headers={
                'X-Auth-Token': self._auth_token_
            }
        )
        #print res.text
        if res.status_code == 200:
            return True
        elif res.status_code in [401, 403]:
            raise UrbaneClientAuthError()
        elif res.status_code == 404:
            raise UrbaneClientError('requested signup not found')
        else:
            raise UrbaneClientError('unable to %s signup' % action)

