#
# Urbane service command line interface
# Copyright: (c) 2016, NephoScale
# Author: Igor V. Dyukov aka div
#

VERSION = '0.1.0'

DEBUG=False

import argparse
import re
import sys

from copy import deepcopy
from os import environ as env
from oslo_utils import encodeutils
from six import print_ as write, text_type
from terminaltables import AsciiTable
from urbaneclient import *
from urlparse import urlparse

# list of 'service' arguments
# NOTE(div): keep in sync with args definition in get_parser()
service_args = [
    'h', 'help',
    'd', 'debug',
    'v', 'version',
    #'create',
    #'update',
    'delete',
    'accept',
    'reject',
    'list',
    'show'
]

# signup states
signup_states = {
    'N': 'New',
    'V': 'Verifying',
    'F': 'Failed',
    'P': 'Pending',
    'X': 'Expired',
    'R': 'Rejected',
    'A': 'Approved'
}

# parse arguments
def _get_parser_():

    parser = argparse.ArgumentParser()

    parser.add_argument('-v', '--version', help='print version and exit', action="store_true")
    parser.add_argument('-d', '--debug', help='turn on debugging', action="store_true")

    parser.add_argument('--os-auth-url', help='authentication URL')
    parser.add_argument('--os-username', help='username to authenticate with')
    parser.add_argument('--os-password', help='password to authenticate with')
    parser.add_argument('--os-tenant', help='tenant name to use with identity API v2')
    parser.add_argument('--os-tenant-name', help='alias for --os-tenant')
    parser.add_argument('--os-project-name', help='alias for --os-tenant')
    parser.add_argument('--os-project', help='alias for --os-tenant')
    parser.add_argument('--os-domain', help='domain name to use with identity API v3')
    parser.add_argument('--os-user-domain-id', help='alias for --os-domain')
    parser.add_argument('--os-version', help='identity API version to use (if not specified by authentication URL)')
    parser.add_argument('--os-identity-api-version', help='alias for --os-version')
    parser.add_argument('--os-region', help='region to use (default: RegionOne)')
    parser.add_argument('--os-region-name', help='alias for --os-region')

    cmd_parsers = parser.add_subparsers(help='list of commands')

#    create_parser = cmd_parsers.add_parser('create', help='create signup')
#    create_account_group = create_parser.add_argument_group('general', 'general account params')
#    create_account_group.add_argument('--username', help='account username', required=True)
#    create_account_group.add_argument('--password', help='account password', required=True)
#    create_parser.add_argument('--organization', help='organization/company name; might be omitted for individuals')
#    create_parser.add_argument('--contact-person', help='contact person full name', required=True)
#    create_parser.add_argument('--contact-address', help='contact address: endpoint, locality, region, zip-code, country', required=True)
#    create_parser.add_argument('--contact-timezone', help='contact timezone', required=True)
#    create_parser.add_argument('--contact-email', help='contact email', required=True)
#    create_parser.add_argument('--contact-phone', help='contact phone (in local or international format)', required=True)
#    create_parser.add_argument('--contact-referral', help='contact referral number')
#    create_parser.add_argument('--billing-cc-holder', help='credit card holder', required=True)
#    create_parser.add_argument('--billing-cc-number', help='credit card number (this value is stored encrypted)', required=True)
#    create_parser.add_argument('--billing-cc-expire', help='credit card expire (mm/yyyy)', required=True)
#    create_parser.add_argument('--billing-cc-secret', help='credit card verification number (this value is never stored)', required=True)
#    create_billing_address = create_parser.add_mutually_exclusive_group(required=True)
#    create_billing_address.add_argument('--billing-use-contact-address', help='use contact address for billing purposes', action="store_true")
#    create_billing_address.add_argument('--billing-address', help='billing address: endpoint, locality, region, zip-code, country; required if --billing-use-contact-address is ommited')
#    create_parser.set_defaults(create=True)

#    update_parser = cmd_parsers.add_parser('update', help='update signup')
#    update_parser.add_argument('id', help='identifier of signup to update')
#    update_parser.add_argument('--username', help='account username')
#    update_parser.add_argument('--password', help='account password')
#    update_parser.add_argument('--organization', help='organization/company name')
#    update_parser.add_argument('--contact-person', help='contact person full name')
#    update_parser.add_argument('--contact-address', help='comma separated contact address: endpoint, locality, region, zip-code, country')
#    update_parser.add_argument('--contact-timezone', help='contact timezone')
#    update_parser.add_argument('--contact-email', help='contact email')
#    update_parser.add_argument('--contact-phone', help='contact phone (in local or international format)')
#    update_parser.add_argument('--contact-referral', help='contact referral number')
#    update_parser.add_argument('--billing-cc-holder', help='credit card holder')
#    update_parser.add_argument('--billing-cc-number', help='credit card number (this value is stored encrypted)')
#    update_parser.add_argument('--billing-cc-expire', help='credit card expire (mm/yyyy)')
#    update_parser.add_argument('--billing-cc-secret', help='credit card verification number (this value is never stored)')
#    update_billing_address = update_parser.add_mutually_exclusive_group()
#    update_billing_address.add_argument('--billing-use-contact-address', help='use contact address for billing purposes; existing billing address will be replaces', action="store_true")
#    update_billing_address.add_argument('--billing-address', help='comma separated billing address: endpoint, locality, region, zip-code, country; required if --billing-use-contact-address is ommited')
#    update_parser.set_defaults(update=True)

    list_parser = cmd_parsers.add_parser('list', help='list signups')
    list_parser.add_argument('--since', help='list signups with creation date since sepcified')
    list_parser.add_argument('--until', help='list signups with creation date until sepcified')
    list_parser.add_argument('--state', help='list signups with sepcified state(s)')
    list_parser.add_argument('--range', help='list signups from range sepcified in one of forms: from_id-till_id | from_id,count | page_number:page_size')
    list_parser.set_defaults(list=True)

    show_parser = cmd_parsers.add_parser('show', help='show specified signup details')
    show_parser.add_argument('id', help='identifier of signup to display')
    show_parser.set_defaults(show=True)

    accept_parser = cmd_parsers.add_parser('accept', help='accept signup')
    accept_parser.add_argument('id', help='identifier of signup to accept')
    accept_parser.set_defaults(action='accept')

    reject_parser = cmd_parsers.add_parser('reject', help='reject signup')
    reject_parser.add_argument('id', help='identifier of signup to reject')
    reject_parser.set_defaults(action='reject')

    delete_parser = cmd_parsers.add_parser('delete', help='delete signup')
    delete_parser.add_argument('id', help='identifier of signup to delete')
    delete_parser.set_defaults(delete=True)

    return parser

# fatal error helper
def fatal(msg):
    print 'Fatal:', msg
    exit(1)

def normalize(args):
    datum = {}
    for arg, val in args.__dict__.iteritems():
        # skip service arguments
        if arg.startswith('os_') or arg in service_args:
            continue
        # set parameter and normalize its value
        datum[arg] = re.sub(r'\s+', ' ', val.strip()) if hasattr(val, 'strip') else val
    return datum


# actual handler
def _exec_(args=None):

    global DEBUG

    KS_API_V = None

    # handle arguments
    if not args:
        args = sys.argv[1:]
    args = [a if isinstance(a, text_type) else a.decode('utf-8') for a in args]

    DEBUG = '-d' in args or '--debug' in args

    if '-v' in args or '--version' in args:
        write('urbane', VERSION)
        exit(0)

    parser = _get_parser_()
    _args_ = parser.parse_args(args)
    # get rid of None args
    args = deepcopy(_args_)
    for arg, val in _args_.__dict__.iteritems():
        if val == None:
            delattr(args, arg)

    # urbane client params
    params = {}

    # determine identity params
    if 'os_auth_url' in args and args.os_auth_url:
        params['auth_url'] = args.os_auth_url
    else:
        params['auth_url'] = env.get('OS_AUTH_URL', None)
    if not params['auth_url']:
        fatal('could not determine identity auth URL')

    if 'os_username' in args and args.os_username:
        params['username'] = args.os_username
    else:
        params['username'] = env.get('OS_USERNAME', None)
    if not params['username']:
        fatal('could not determine identity username')

    if 'os_password' in args and args.os_password:
        params['password'] = args.os_password
    else:
        params['password'] = env.get('OS_PASSWORD', None)
    if not params['password']:
        fatal('could not determine identity password')

    params['region'] = getattr(args, 'os_region', getattr(args, 'os_region_name', env.get('OS_REGION', env.get('OS_REGION_NAME', 'stage2'))))

    # determine identity API version
    auth_url_path = urlparse(params['auth_url']).path

    # API v2
    if auth_url_path.startswith('/v2'):
        KS_API_V = 2.0

    # API v3
    elif auth_url_path.startswith('/v3'):
        KS_API_V = 3.0

    # API version specified by command line argument or by environment variable
    else:
        ver = getattr(args, 'os_identity_api_version', getattr(args, 'os_version', env.get('OS_IDENTITY_API_VERSION', env.get('OS_VERSION', None))))
        if not ver:
            fatal('unable to determine identity API version')

        if ver in [2, '2', '2.0']:
            KS_API_V = 2.0
            # adjust auth_url
            params['auth_url'] += '/v2.0'

        elif ver in [3, '3', '3.0']:
            KS_API_V = 3.0
            # adjust auth_url
            params['auth_url'] += '/v3'

        else:
            fatal('unsupported or invalid identity API version')

    if DEBUG:
        print "DEBUG:", "using identity API version", KS_API_V

    # set version specific params
    if KS_API_V == 2.0:
        if 'os_project_name' in args and args.os_project_name:
            params['tenant'] = args.os_project_name
        if 'os_tenant_name' in args and args.os_tenant_name:
            params['tenant'] = args.os_tenant_name
        elif 'os_project' in args and args.os_project:
            params['tenant'] = args.os_project
        elif 'os_tenant' in args and args.os_tenant:
            params['tenant'] = args.os_tenant
        else:
            params['tenant'] = env.get('OS_PROJECT_NAME', env.get('OS_TENANT_NAME', env.get('OS_PROJECT', env.get('OS_TENANT', None))))
        if not params['tenant']:
            fatal('unable to determine identity project/tenant')

    elif KS_API_V == 3.0:
        if 'os_project_name' in args and args.os_project_name:
            params['tenant'] = args.os_project_name
        if 'os_tenant_name' in args and args.os_tenant_name:
            params['tenant'] = args.os_tenant_name
        elif 'os_project' in args and args.os_project:
            params['tenant'] = args.os_project
        elif 'os_tenant' in args and args.os_tenant:
            params['tenant'] = args.os_tenant
        else:
            params['tenant'] = env.get('OS_PROJECT_NAME', env.get('OS_TENANT_NAME', env.get('OS_PROJECT', env.get('OS_TENANT', 'admin'))))
        if not params['tenant']:
            fatal('unable to determine identity project/tenant')

        if 'os_user_domain_id' in args and args.os_user_domain_id:
            params['domain'] = args.os_user_domain_id
        elif 'os_domain' in args and args.os_domain:
            params['domain'] = args.os_domain
        
        else:
            #params['domain'] = env.get('OS_USER_DOMAIN_ID', env.get('OS_DOMAIN', None))
            params['domain'] = env.get('OS_USER_DOMAIN_ID', env.get('OS_USER_DOMAIN_NAME', env.get('OS_PROJECT_DOMAIN_ID', env.get('OS_PROJECT_DOMAIN_NAME', env.get('OS_DOMAIN', None)))))
        if not params['domain']:
            fatal('unable to determine identity domain')

    else:
        fatal('invalid identity API version')
     
    params['username'] = 'admin'
    params['password'] = 'qSGbg3tBAmU6'
    params['auth_url'] = 'https://api.stage2.nephoscale.net:5000/v3'
    params['domain']   = 'default'
    params['project']  = 'admin'
    
    # instantiate Urbane (signup) client
    signups = Client(**params)

    # create signup
    if getattr(args, 'create', False):

        # prepare signup datum
        datum = normalize(args)

        # special data
        datum['confirm_password'] = datum['password']
        datum['accept_agreement'] = True

        try:
            signups.create(**datum)

        except UrbaneClientDataError as e:
            write('Invalid data provided:')
            for error in e.errors:
                write('  %-30s%s' % ('--' + error.replace('_', '-'), e.errors[error]))


    # update signup
    elif getattr(args, 'update', False):

        if not hasattr(args, 'id'):
            raise UrbaneClientException('signup identifier expected')

        # prepare signup datum
        datum = normalize(args)

        try:
            signups.update(**datum)

        except UrbaneClientDataError as e:
            write('Invalid data provided:')
            for error in e.errors:
                write('  %-30s%s' % ('--' + error.replace('_', '-'), e.errors[error]))

    # delete signup(s)
    elif getattr(args, 'delete', False):
        datum = normalize(args)
        signups.delete(**datum)

    # list signups
    elif getattr(args, 'list', False):
        (result, total) = signups.list(format='common')
        print result
        print '++++++++++++++++++++++++++++++'
        if not result:
            write('No data...')
            return
        data = [
            ['Signup Id', 'Created At', 'Username', 'Score', 'State', 'Organization', 'Contact Person', 'Contact Phone']
        ]
        for signup in result:
            data.append((
                signup.id,
                signup.cdate,
                signup.username,
                signup.score,
                signup_states[signup.state],
                signup.organization or '-',
                signup.contact_person or '#ERROR!',
                signup.contact_phone or '#ERROR!'
            ))
        output = AsciiTable(data)
        write(output.table)

    # show signup details
    elif getattr(args, 'show', False):
        signup = signups.get(id = args.id)
        print 'Signup ID:             ', signup.id
        print 'Create Timestamp:      ', signup.cdate
        print 'Username:              ', signup.username
        print 'Score:                 ', signup.score
        print 'State:                 ', signup_states[signup.state]
        print 'Extra:                 ', signup.extra
        print 'Datum:'
        print '  Organization:        ', signup.organization or '-'
        print '  Contact Person:      ', signup.contact_person
        print '  Contact Address:     ', signup.contact_address
        print '  Contact Email:       ', signup.contact_email
        print '  Contact Phone:       ', signup.contact_phone
        print '  Contact Referral:    ', signup.contact_referral or '-'
        print '  Billing Address:     ', signup.billing_address
        print '  Credit Card Holder:  ', signup.billing_cc_holder
        print '  Credit Card Number:  ', signup.billing_cc_number
        print '  Credit Card Expire:  ', signup.billing_cc_expire

    elif getattr(args, 'action', False):
        signups.action(id=args.id, action=args.action)
    else:
        raise Exception('invalid arguments')

# *** entry point ***
def main(args=None):
    try:
        _exec_(args)

    except KeyboardInterrupt:
        write('Keyboard interrupt. Halting...', file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        # handle runtime error
        if DEBUG:
            raise
        else:
            write('Fatal: %s. Halting...' % encodeutils.safe_encode(text_type(e)), file=sys.stderr)


if __name__ == '__main__':
    main()
