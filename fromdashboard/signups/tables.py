from django.core.exceptions import ValidationError  # noqa
from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import messages
from horizon import exceptions
from horizon import forms
from horizon import tables

from urbaneclient import Client as UrbaneClient
from openstack_dashboard.local.local_settings import ADMIN_USERNAME, \
                                                     ADMIN_PASSWORD, \
                                                     ADMIN_TENANT, \
                                                     ADMIN_DOMAIN, \
                                                     ADMIN_REGION, \
                                                     ADMIN_AUTH_URL

from openstack_dashboard.dashboards.identity.signups.common import get_admin_ksclient, \
                                                                   get_urbaneclient

signup_state = {
    'N': 'New',
    'V': 'Verifying',
    'F': 'Failed',
    'P': 'Pending',
    'X': 'Expired',
    'R': 'Rejected',
    'A': 'Accepted'
}

get_signup_state = lambda v: signup_state.get(v, 'Unknown')

class SignupAcceptAction(tables.actions.BatchAction):
    name = 'signup_accept'
    verbose_name = _('Accept')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Accept",
            u"Accept",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Accepted Signup",
            u"Accepted Signups",
            count
        )

    def allowed(self, request, signup):
        return signup.state in ['N', 'V', 'P']

    def action(self, request, id):
        uclient = get_urbaneclient()
        uclient.action(id, 'accept')

class SignupRejectAction(tables.actions.BatchAction):
    name = 'signup_reject'
    verbose_name = _('Reject')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Reject",
            u"Reject",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Rejected Signup",
            u"Rejected Signups",
            count
        )
    def allowed(self, request, signup):
        return signup.state in ['N', 'V', 'P']

    def action(self, request, id):
        uclient = get_urbaneclient()
        uclient.action(id, 'reject')

class SignupDeleteAction(tables.DeleteAction):
    name = 'signup_delete'
    verbose_name = _('Delete')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete",
            u"Delete",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Signup",
            u"Deleted Signups",
            count
        )

    def delete(self, request, id):
        uclient = get_urbaneclient()
        uclient.delete(id)

#Section related to Modify/Update Domain option
class ModifyDomain(tables.LinkAction):
    name = 'modify_domain'
    verbose_name = _('Update Domain')
    url = 'horizon:identity:signups:modify_domain'
    ajax = True
    classes = ('ajax-modal',)

    #Modify Domain menu must be visible only for New Users
    def allowed(self, request, signup):
        return signup.state in ['N', 'V', 'P']

class SignupsTable(tables.DataTable):
    id = tables.Column(
        'id',
        verbose_name = _('Signup ID'),
        link = ('horizon:identity:signups:detail')
    )
    cdate = tables.Column(
        'cdate',
        verbose_name = _('Created At')
    )
    username = tables.Column(
        'username',
        verbose_name = _('Username')
    )
    domain  = tables.Column(
        'domain',
        verbose_name = _('Domain')
    )
    # score = tables.Column(
    #     'score',
    #     verbose_name = _('Score')
    # )
    state = tables.Column(
        'state',
        verbose_name = _('State'),
        filters=(get_signup_state,)
    )
    organization = tables.Column(
        'organization',
        verbose_name = _('Organization')
    )
    contact_person = tables.Column(
        'contact_person',
        verbose_name = _('Contact Person')
    )
    contact_phone = tables.Column(
        'contact_phone',
        verbose_name = _('Contact Phone')
    )

    _page_ = 1

    def get_pagination_string(self):
        return '_page_=' + str(self._page_ + 1)

    def get_prev_pagination_string(self):
        return '_page_=' + str(self._page_ - 1) if self._page_ > 1 else None

    class Meta(object):
        name = 'signups'
        verbose_name = _('Signups')

        row_actions = (ModifyDomain, SignupAcceptAction, SignupRejectAction, SignupDeleteAction)
        #table_actions = ()

        pagination_param = '_page_'
