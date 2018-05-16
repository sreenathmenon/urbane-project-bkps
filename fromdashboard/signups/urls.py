from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.identity.signups import views


urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^(?P<signup_id>[^/]+)/detail/$',views.DetailView.as_view(), name='detail'),
    url(r'^(?P<id>[^/]+)/modify_domain/$',views.ModifyDomainView.as_view(),name='modify_domain'),
)
