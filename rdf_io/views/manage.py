# # -*- coding:utf-8 -*-
from django.shortcuts import render_to_response, redirect
from rdf_io.models import ObjectMapping,Namespace,AttributeMapping,EmbeddedMapping, ObjectType, getattr_path, apply_pathfilter, expand_curie, dequote
from rdf_io.views import get_rdfstore,publish
from django.template import RequestContext
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from string import Formatter
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

import json

import logging
logger = logging.getLogger(__name__)

def show_config(request) :
    return HttpResponse(json.dumps( settings.RDFSTORE ))

def sync_remote(request,models):
    """
        Synchronises the RDF published output for the models, in the order listed (list containers before members!)
    """
    if request.GET.get('pdb') :
        import pdb; pdb.set_trace()
 
    for model in models.split(",") :
        try:
            (app,model) = model.split('.')
            ct = ContentType.objects.get(app_label=app,model=model)
        except:
            ct = ContentType.objects.get(model=model)
        if not ct :
            raise Http404("No such model found")

        try:
            rdfstore = get_rdfstore(model,name=request.GET.get('rdfstore') )
        except Exception as e:
            return  HttpResponse("RDF store not configured for model %s threw %s"  % (model,e) , status=410 )

        do_sync_remote( model, ct , rdfstore )
    return HttpResponse("sync successful for {}".format(models), status=200)
    
def do_sync_remote(formodel, ct ,rdfstore):

    oml = ObjectMapping.objects.filter(content_type=ct)
    modelclass = ct.model_class()
    for obj in modelclass.objects.all() :
        publish( obj, formodel, oml, rdfstore)
# gr.add((URIRef('skos:Concept'), RDF.type, URIRef('foaf:Person')))
# gr.add((URIRef('rdf:Concept'), RDF.type, URIRef('xxx:Person')))

def ctl_signals(request,cmd):
    """utility view to control and debug signals"""
    from rdf_io.signals import setup_signals,list_pubs,sync_signals
    if cmd == 'on':
        msg = auto_on()
    elif cmd == 'off' :
        msg = "not implemented"
    elif cmd == 'list' :
        msg = list_pubs()
    elif cmd == 'sync' :
        msg = sync_signals()
    elif cmd == 'help' :
        msg = "usage /rdf_io/ctl_signals/(on|off|list|sync|help)"
    else:
        msg = "Command %s not understood. Use /rdf_io/ctl_signals/help for valid commands" % cmd
    return HttpResponse(msg, status=200)
 

def auto_on():
    """turn Auto push signals on"""
    from rdf_io.signals import setup_signals,list_pubs
    signals.post_save.connect(setup_signals, sender=ObjectMapping)
    return list_pubs()

    
    
