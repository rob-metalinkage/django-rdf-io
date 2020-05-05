# Geonode installation notes
(may apply to other bundled django applications, where mod_wsgi is used to connect to django)

# note this is out of date - should be revisited now Geonode has migrated to django 2.2

# Use Case
an existing django application has been installed on unbuntu using apt-get

This is challenging as its not obvious where things are configured and how to propagate changes. Here are notes from going through this process - if there is a better way please document it here and throw these away!

# Installing new apps

This is standard process - up to a point..

install django modules - into the same environment you app is installed - note that using the apt-get method means the app is globally installed, not into a virtualenv, and hence most of the django developer docs are no longer relevant

set up django-admin to use the default app  :
 - this is tricky because with apt-get installation you do not get the containing django project directory with manage.py - at least I could not find if/where this was available in the default installation
e.g. 
mkdir /usr/share/django-apps
cd /usr/share/django-apps
ln -s /usr/local/lib/python2.7/dist-packages/geonode .
create a manage.py in /usr/share/django-apps 
edit so settings are geonode/settings ( note, you cannot run this inside geonode because of conflicts between imported module "geoserver" and local module! -


now we need to make the installed app know about the extensions:
edit geonode/settings (eg local_settings.py) to include new packages in INSTALLED_APPS, and other settings required (RDFSTORE)
edit geonode/urls.py 

run python manage.py syncdb

NB this will load initial data 

## TODO
work out how signals to publish to remote RDFSTORE survive this installation process

# to propagate configuration changes to running server:

touch /var/www/geonode/wsgi/geonode.wsgi

load some content for which RDF mappings exist
test : 

## to get into debug mode on the server

one way to test stuff is:
python manage.py shell

* import all the things in the module you want to invoke so you can run methods and interact with object types:
`from django.shortcuts import render_to_response, redirect
from rdf_io.models import ObjectMapping,Namespace,AttributeMapping, ObjectType, getattr_path
from django.template import RequestContext
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from string import Formatter
import requests
`

* set up debugger:
* set up breakpoint
* back to shell:
* call function to debug

eg
`
import pdb; pdb.set_trace()
b rdf_io/views:217
c
from rdf_io.views import do_sync_remote
do_sync_remote('scheme')
`

