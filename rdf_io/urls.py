from django.urls import path
try:
    from .views import ctl_signals,show_config,sync_remote,to_rdfbyid,pub_rdf, to_rdfbykey
except:
    from views import ctl_signals,show_config,sync_remote,to_rdfbyid,pub_rdf, to_rdfbykey
    
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    # path(r'^$', 'rdf_io.views.home', name='home'),
    # path(r'^blog/', include('blog.urls')),
    #path('to_rdf/(?P<model>[^\/]+)/id/(?P<id>\d+)$', to_rdfbyid, name='to_rdfbyid'),
    path('to_rdf/<str:model>/id/<int:id>/', to_rdfbyid, name='to_rdfbyid'),
    #old: url('to_rdf/(?P<model>[^\/]+)/key/(?P<key>.+)$', to_rdfbykey, name='to_rdfbykey'),
    path('to_rdf/<str:model>//key/<str:key>/', to_rdfbykey, name='to_rdfbykey'),
    # old: url('pub_rdf/(?P<model>[^\/]+)/(?P<id>\d+)$', pub_rdf, name='pub_rdf'),
    path('pub_rdf/<str:model>/<int:id>/', pub_rdf, name='pub_rdf'),
    # management urls - add user auth
    # old: url('sync_remote/(?P<models>[^\/]+)$', sync_remote, name='sync_remote'),
    path('sync_remote/<str:model>/', sync_remote, name='sync_remote'),
    path('show_config/', show_config, name='show_config'),
    # old url ('ctl_signals/(?P<cmd>[^\/]+)$', ctl_signals, name='ctl_signals'),
    path('ctl_signals/<str:cmd>/', ctl_signals, name='ctl_signals'),
    # path(r'^admin/', include(admin.site.urls)),
]
