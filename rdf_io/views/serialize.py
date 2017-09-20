# # -*- coding:utf-8 -*-
from django.shortcuts import render_to_response, redirect
from rdf_io.models import ObjectMapping,Namespace,AttributeMapping,EmbeddedMapping, ObjectType,ServiceBinding, getattr_path, apply_pathfilter, expand_curie, dequote, push_to_store

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



import logging
logger = logging.getLogger(__name__)

_nslist = {}

def _getNamespace( prefix ) :
    if not _nslist.has_key( prefix ) :
         ns = Namespace.objects.get(prefix = prefix)
         if ns: 
            _nslist[ prefix ] = ns.uri
         else :
            _nslist[ prefix ] = None
    return _nslist[prefix]
  
def _as_resource(gr,curie) :
    cleaned = dequote(curie)
    if cleaned[0:4] == 'http' :
        return URIRef(cleaned)
    # this will raise error if not valid curie format
    try:
        (ns,value) = cleaned.split(":",2)
    except:
        raise ValueError("value not value HTTP or CURIE format %s" % curie)    
    try :
        return URIRef("".join((_getNamespace(ns),value)))
    except:
        raise ValueError("prefix " + ns + "not recognised")
 
 
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
 
    includemembers = False
    
    gr = Graph()
#    import pdb; pdb.set_trace()
#    ns_mgr = NamespaceManager(Graph())
#    gr.namespace_manager = ns_mgr
    try:
        gr = build_rdf(gr, obj, oml, includemembers)
    except Exception as e:
        raise Http404("Error during serialisation: " + str(e) )
    for ns in _nslist.keys() :
        gr.namespace_manager.bind( str(ns), namespace.Namespace(str(_nslist[ns])), override=False)
    return HttpResponse(content_type="text/turtle", content=gr.serialize(format=format))

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
    
    if name :
        rdfstore_cfg = settings.RDFSTORES[name]
    else:
        rdfstore_cfg = settings.RDFSTORE
    rdfstore = rdfstore_cfg['default']
    auth = rdfstore.get('auth')
    server = rdfstore['server']
    server_api = rdfstore['server_api']
       
    try:
        rdfstore = rdfstore_cfg[model]
        if not rdfstore.has_key('server') :
            rdfstore['server'] = server
            rdfstore['auth'] = auth
        if not rdfstore.has_key('server_api') :
            rdfstore['server_api'] = server_api            
    except:
        pass  # use default then
    
    return rdfstore
    
def publish(obj, model, oml, rdfstore ):
      
       
    gr = Graph()
#    import pdb; pdb.set_trace()
#    ns_mgr = NamespaceManager(Graph())
#    gr.namespace_manager = ns_mgr
    try:
        gr = build_rdf(gr, obj, oml, False)
    except Exception as e:
        raise Exception("Error during serialisation: " + str(e) )
    for ns in _nslist.keys() :
        gr.namespace_manager.bind( str(ns), namespace.Namespace(str(_nslist[ns])), override=False)
    
#    curl -X POST -H "Content-Type: text/turtle" -d @- http://192.168.56.151:8080/marmotta/import/upload?context=http://mapstory.org/def/featuretypes/gazetteer 
    
    
    return push_to_store( None, model, obj, gr )

 
   
def build_rdf( gr,obj, oml, includemembers ) :  

    # would be nice to add some comments : as metadata on the graph? '# Turtle generated by django-rdf-io configurable serializer\n'  
    for om in oml :
        # check filter
        objfilter = getattr(om,'filter') 
        if objfilter and not apply_pathfilter(obj, objfilter ) :
            continue
        try:
            tgt_id = getattr_path(obj,om.id_attr)[0]
        except ValueError as e:
            raise ValueError("target id attribute {} not found".format( (om.id_attr ,)))
        if om.target_uri_expr[0] == '"' :   
            uribase = om.target_uri_expr[1:-1]
        else:
            uribase = getattr_path(obj,om.target_uri_expr)[0]
            
        tgt_id = str(tgt_id).replace(uribase,"")
        # strip uri base if present in tgt_id
        uribase = expand_curie(uribase)
        
 
        if not tgt_id:
            uri = uribase
        elif uribase[-1] == '/' or uribase[-1] == '#' :
            uri = "".join((uribase,tgt_id))
        else :
            uri = "/".join((uribase,tgt_id))
        
        subject = URIRef(uri)
        
        for omt in om.obj_type.all() :
            gr.add( (subject, RDF.type , _as_resource(gr,omt.uri)) )
  
        # now get all the attribute mappings and add these in
        for am in AttributeMapping.objects.filter(scope=om) :
            _add_vals(gr, obj, subject, am.predicate, am.attr , am.is_resource)
        for em in EmbeddedMapping.objects.filter(scope=om) :
            try:
                # three options - scalar value in which case attributes relative to basic obj, a mulitvalue obj or we have to look for related objects
                try:
                    valuelist = getattr_path(obj,em.attr)
                except:
                    valuelist = [obj,] 

                for value in valuelist :
                    newnode = None
 
                    for element in em.struct.split(";") :
                        try:
                            (predicate,expr) = element.split()
                        except:
                            predicate = None
                            expr = element
                            
                        # resolve any internal template parameters {x}
                        expr = expr.replace("{$URI}", uri )

                        is_resource = False
                        if expr.startswith("<") :
                            is_resource = True
                            expr = expr[1:-1].join(('"','"'))
                        elif expr.startswith("/") :
                            #value relativeto root obj  - retrieve and use as literal
                            try:
                                expr = iter(getattr_path(obj,expr[1:])).next()
                                if type(expr) == str :
                                    expr = expr.join( ('"','"'))
                            except:
                                raise ValueError( "Could not access value of %s from mapped object %s (/ is relative to the object being mapped" % (expr,obj) )
                        else:
                            is_resource = False
                        
                        for (lit,var,x,y) in Formatter().parse(expr) :
                            if var :
                                try:
                                    if var.startswith("^"):
                                        val = iter(getattr_path(obj,var[1:])).next()
                                    else:
                                        val = iter(getattr_path(value,var)).next()
                                    
                                    if is_resource:
                                        try:
                                            val = u.urlencode({ 'v' : val.encode('utf-8')})[2:]
                                        except:
                                            #not a string, just pass
                                            pass
                                    val = str(val)
                                except:
                                    val="{!variable not found : %s}" % var
                                expr = expr.replace(var.join(("{","}")), val )
                        if predicate :
                            # an internal struct has been found so add a new node if not ye done
                            if not newnode:
                                newnode = BNode()
                                gr.add( (subject, _as_resource(gr,em.predicate) , newnode) )
                            _add_vals(gr, value, newnode, predicate, expr , is_resource)
                        else:
                            # add to parent
                            _add_vals(gr, value, subject, em.predicate, expr , is_resource)
            except Exception as e:
                import traceback; import sys; traceback.print_exc()
                print "Could not evaluate extended mapping %s : %s " % (e,em.attr), sys.exc_info()
                raise ValueError("Could not evaluate extended mapping %s : %s " % (e,em.attr))
    # do this after looping through all object mappings!
    return gr

def _add_vals(gr, obj, subject, predicate, attr, is_resource ) :       
            if type(attr) == float or attr[0] in '\'\"' : # then a literal
                if is_resource :
                    gr.add( (subject, _as_resource(gr,predicate) , _as_resource(gr,attr) ) )
                else:
                    try:
                        (str,lang) = attr.split('@')
                        gr.add( (subject, _as_resource(gr,predicate) , Literal(dequote(str),lang=lang) ))
                    except:
                        gr.add( (subject, _as_resource(gr,predicate) , Literal(dequote(attr)) ))
            else :
                values = getattr_path(obj,attr)
                for value in values :
                    if not value :
                        continue
                    if is_resource :
                        object = _as_resource(gr,value)
                    else:
                        try:
                            try :
                                (value,valtype) = value.split("^^")
                                object = Literal(value,datatype=valtype)
                            except:
                                try :
                                    (value,valtype) = value.split("@")
                                    object = Literal(value,lang=valtype)
                                except:
                                    object = Literal(value)
                        except:
                            raise ValueError("Value not a convertable type %s" % type(value))
                    gr.add( (subject, _as_resource(gr,predicate) , object) )
