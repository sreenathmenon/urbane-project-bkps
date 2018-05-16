from django.utils.translation import ugettext_lazy as _
import horizon

from openstack_dashboard.local.local_settings import SIGNUP_ROLES, OPENSTACK_API_VERSIONS
from openstack_dashboard.dashboards.identity.signups.common import get_admin_ksclient

class Signups(horizon.Panel):
    name = _("Signups")
    slug = 'signups'

    #Only the following roles are allowed to access this dashboard
    permissions = (('openstack.roles.admin',
                  ),)