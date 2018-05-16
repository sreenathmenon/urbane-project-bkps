#
# Copyright 2017 NephoScale
#

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import exceptions

from openstack_dashboard import api
from openstack_dashboard.api import keystone
from openstack_dashboard.dashboards.identity.signups.common import get_admin_ksclient, \
                                                                   get_urbaneclient

#Fetching the domain details for displaying in the drod-down for updating the domain of a signup
def gen_domain_list(request):

    #Initialization
    data = []
    domain_list = keystone.domain_list(request)
    for domain in domain_list:

        #Fetching the name and id of domain
        dom_name = getattr(domain, 'name', None)
        dom_id   = getattr(domain, 'id', None)
        data.append((dom_id, _(dom_name)))
    return data

class ModifyDomainForm(forms.SelfHandlingForm):

    id       = forms.CharField(label=_("ID"), widget=forms.HiddenInput())
    domain   = forms.ChoiceField(label=_("Edit Domain"), required=True,  widget=forms.Select, choices=[])

    def __init__(self, request, *args, **kwargs):
        super(ModifyDomainForm, self).__init__(request, *args, **kwargs)
        id = kwargs.get('initial', {}).get('id')
        self.fields['id'].initial      = id
        self.fields['domain'].choices  = gen_domain_list(request)

    def handle(self, request, data):
        
        id = data.get('id')
        try:
            uclient = get_urbaneclient()
            uclient.update(data)
            msg = _('Domain has been updated successfully')
            messages.success(request, msg)
        except Exception, e:
            redirect = reverse('horizon:identity:signups:index')
            exceptions.handle(request, _("Unable to update the domain!"), redirect=redirect)
        return True
