#
# Copyright 2017 NephoScale
#

from django.conf import settings
from horizon.exceptions import HorizonException
from horizon.utils import functions as utils
from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import keystone

from openstack_dashboard.local.local_settings import \
                                        ADMIN_AUTH_URL, \
                                        ADMIN_USERNAME, \
                                        ADMIN_PASSWORD, \
                                        ADMIN_TENANT, \
                                        ADMIN_DOMAIN, \
                                        ADMIN_REGION, \
                                        KEYSTONE_ADMIN_PROJECT_NAME, \
                                        KEYSTONE_ADMIN_PROJECT_DOMAIN_NAME, \
                                        KEYSTONE_ADMIN_USER_DOMAIN_NAME, \
                                        OPENSTACK_API_VERSIONS

if OPENSTACK_API_VERSIONS['identity'] >= 3:
    from keystoneclient.v3 import client as ksclient
else:
    from keystoneclient.v2_0 import client as ksclient

from urbaneclient import Client as UrbaneClient

#Added for Custom Keystoneclient connection
def get_admin_ksclient():

    if OPENSTACK_API_VERSIONS['identity'] >= 3:
        keystone = ksclient.Client(
            auth_url            = getattr(settings, 'ADMIN_AUTH_URL', None),
            username            = getattr(settings, 'ADMIN_USERNAME', None),
            password            = getattr(settings, 'ADMIN_PASSWORD', None),
            tenant              = getattr(settings, 'ADMIN_TENANT', None),
            domain              = getattr(settings, 'ADMIN_DOMAIN', None),
            region              = getattr(settings, 'ADMIN_REGION', None),
            user_domain_name    = getattr(settings, 'KEYSTONE_ADMIN_USER_DOMAIN_NAME', None),
            project_domain_name = getattr(settings, 'KEYSTONE_ADMIN_PROJECT_DOMAIN_NAME', None),
        )
        keystone.tenants = keystone.projects
    else:
        keystone = ksclient.Client(
            username    = getattr(settings, 'ADMIN_USERNAME', None),
            password    = getattr(settings, 'ADMIN_PASSWORD', None),
            tenant_name = getattr(settings, 'ADMIN_TENANT', None),
            auth_url    = getattr(settings, 'ADMIN_AUTH_URL', None),
        ) 
    return keystone

def get_urbaneclient():

    # urbane client automatically discovers
    # Keystone API version from auth_url
    # and takes required parameter
    urbane = UrbaneClient(
        auth_url            = getattr(settings, 'ADMIN_AUTH_URL', None),
        username            = getattr(settings, 'ADMIN_USERNAME', None),
        password            = getattr(settings, 'ADMIN_PASSWORD', None),
        tenant              = getattr(settings, 'ADMIN_TENANT', None),
        domain              = getattr(settings, 'ADMIN_DOMAIN', None),
        region              = getattr(settings, 'ADMIN_REGION', None),
        user_domain_name    = getattr(settings, 'KEYSTONE_ADMIN_USER_DOMAIN_NAME', None),
        project_domain_name = getattr(settings, 'KEYSTONE_ADMIN_PROJECT_DOMAIN_NAME', None),
    ) 
    return urbane

