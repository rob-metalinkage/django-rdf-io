from django.conf.urls import patterns, include, url
from .views import to_rdf, pub_rdf, sync_remote
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'rdf_io.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'to_rdf/(?P<model>[^\/]+)/(?P<id>\d+)$', to_rdf, name='to_rdf'),
    url(r'pub_rdf/(?P<model>[^\/]+)/(?P<id>\d+)$', pub_rdf, name='pub_rdf'),
    url(r'sync_remote/(?P<models>[^\/]+)$', sync_remote, name='sync_remote'),
    url(r'^admin/', include(admin.site.urls)),
)
