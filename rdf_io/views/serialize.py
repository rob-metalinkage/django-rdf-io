# # -*- coding:utf-8 -*-
#from django.shortcuts import render, redirect
from rdf_io.models import *
from ..protocols import push_to_store,inference,rdf_delete

from django.template import RequestContext
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from rdflib import BNode
# TODO make python 3 safe!
import urllib as u
import requests

from django.db.models import signals

from django.shortcuts import get_object_or_404
# deprecated since 1.3
# from django.views.generic.list_detail import object_list
# but not used anyway?
# if needed.. from django.views.generic import ListView

from django.http import HttpResponse,Http404

from rdflib import Graph,namespace
from rdflib.term import URIRef, Literal
from rdflib.namespace import NamespaceManager,RDF

import sys

import logging
logger = logging.getLogger(__name__)

_nslist = {}


def to_rdfbykey(request,model,key):
    """
        take a model name + object id reference to an instance and apply any RDF serialisers defined for this
        allows a key to de appended to the uri or supplied by parameter (easier for uri values)
    """
    if request.GET.get('key'):
        key = request.GET.get('key')
    try: 
        return _tordf(request,model,None,key)
    except Exception as e: 
        return HttpResponse("Model not serialisable to RDF: %s" % e, status=500)
 
def to_rdfbyid(request,model,id):
    """
        take a model name + object id reference to an instance and apply any RDF serialisers defined for this
    """
    try: 
        return _tordf(request,model,id,None)
    except Exception as e: 
        return HttpResponse("Model not serialisable to RDF: %s" % e, status=500)

def _tordf(request,model,id,key):
    if request.GET.get('pdb') :
        import pdb; pdb.set_trace()
    format = request.GET.get('_format')
    if format not in ('turtle','json-ld'):
        if format == 'json':
            format = "json-ld"
        else:
            format = "turtle"

    # find the model type referenced
    try:
        (app,model) = model.split('.')
        ct = ContentType.objects.get(app_label=app,model=model)
    except:
        ct = ContentType.objects.get(model=model)
    if not ct :
        raise Http404("No such model found")
    oml = ObjectMapping.objects.filter(content_type=ct)
    if not oml :
        return HttpResponse("Model not serialisable to RDF", status=410 )
    if id :    
        obj = get_object_or_404(ct.model_class(), pk=id)
    else :
        try:
            obj = ct.model_class().objects.get_by_natural_key(key)
        except Exception as e:
            try:
                (prefix,term) = key.split(':')
                ns = Namespace.objects.get(prefix=prefix)
                urikey = "".join((ns.uri,term))
                obj = ct.model_class().objects.get_by_natural_key(urikey)
            except Exception as e2:
                raise e
    
    # ok so object exists and is mappable, better get down to it..
 
    includemembers = True
    if request.GET.get('skip') :
        includemembers = request.GET.get('skip') != 'True'
        
    gr = Graph()
#    import pdb; pdb.set_trace()
#    ns_mgr = NamespaceManager(Graph())
#    gr.namespace_manager = ns_mgr
    try:
        gr = build_rdf(gr, obj, oml, includemembers)
    except Exception as e:
        raise Http404("Error during serialisation: " + str(e) )
    return HttpResponse(content_type="text/turtle; charset=utf-8", content=gr.serialize(format=format))

def pub_rdf(request,model,id):
    """
        take a model name + object id reference to an instance serialise and push to the configured triplestore
    """
    if request.GET.get('pdb') :
        import pdb; pdb.set_trace()
    # find the model type referenced
    try:
        (app,model) = model.split('.')
        ct = ContentType.objects.get(app_label=app,model=model)
    except:
        ct = ContentType.objects.get(model=model)
    if not ct :
        raise Http404("No such model found")
    oml = ObjectMapping.objects.filter(content_type=ct)
    if not oml :
        raise HttpResponse("Model not serialisable to RDF", status=410 )
    
    obj = get_object_or_404(ct.model_class(), pk=id)
    # ok so object exists and is mappable, better get down to it..

    try:
        rdfstore = get_rdfstore(model,name=request.GET.get('rdfstore') )
    except:
        return  HttpResponse("RDF store not configured", status=410 )
    
    try:
        result = publish(obj, model, oml,rdfstore)
    except Exception as e:
        return HttpResponse("Exception publishing remote RDF content %s" % e,status=500 )
    return HttpResponse("Server reports %s" % result.content,status=result.status_code )
    
def get_rdfstore(model, name=None ):
    # now get the remote store mappings 
    # deprecated - using ConfigVar and ServiceBindings now..
    # print "Warning - deprecated method invoked - use ServiceBindings instead of static config now"
    return None
    # if name :
        # rdfstore_cfg = settings.RDFSTORES[name]
    # else:
        # rdfstore_cfg = settings.RDFSTORE
    # rdfstore = rdfstore_cfg['default']
    # auth = rdfstore.get('auth')
    # server = rdfstore['server']
    # server_api = rdfstore['server_api']
       
    # try:
        # rdfstore = rdfstore_cfg[model]
        # if not rdfstore.has_key('server') :
            # rdfstore['server'] = server
            # rdfstore['auth'] = auth
        # if not rdfstore.has_key('server_api') :
            # rdfstore['server_api'] = server_api            
    # except:
        # pass  # use default then
    
    # return rdfstore

def publish_set(queryset, model,check=False,mode='PUBLISH'):
    """ publish select set of objects of type "model" 
    
    Because this may be long running it is a status message generator
    """
    oml = ObjectMapping.objects.filter(content_type__model=model)
    for obj in queryset :
        if check:
            try:
                yield ("checking %s " % (obj.uri,))
                resp = u.urlopen(obj.uri)
                if resp.getcode() == 200 :
                    continue
            except Exception as e :
                yield("Exception: %s" % (str(e), ) )
        yield ("publishing %s " % (obj,) )
        try:
            # import pdb; pdb.set_trace()
            publish( obj, model, oml,mode=mode)
            yield ("... Success")
        except Exception as e :
            yield("Exception %s" % (str(e), ) ) 
   
    
