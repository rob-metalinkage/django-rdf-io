from django.conf.urls import url
from .views import to_rdfbyid,to_rdfbykey, pub_rdf, sync_remote,ctl_signals
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    # url(r'^$', 'rdf_io.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'to_rdf/(?P<model>[^\/]+)/id/(?P<id>\d+)$', to_rdfbyid, name='to_rdfbyid'),
    url(r'to_rdf/(?P<model>[^\/]+)/key/(?P<key>.+)$', to_rdfbykey, name='to_rdfbykey'),
    url(r'pub_rdf/(?P<model>[^\/]+)/(?P<id>\d+)$', pub_rdf, name='pub_rdf'),
    url(r'sync_remote/(?P<models>[^\/]+)$', sync_remote, name='sync_remote'),
    url(r'ctl_signals/(?P<cmd>[^\/]+)$', ctl_signals, name='ctl_signals'),
    # url(r'^admin/', include(admin.site.urls)),
]
