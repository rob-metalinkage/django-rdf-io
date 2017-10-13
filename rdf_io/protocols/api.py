from django.db import models
from django.conf import settings
import os
import rdflib

import requests

# from rdf_io.models import ServiceBinding
from string import Formatter

class RDFConfigNotFoundException(Exception):
    """ Cannot find a RDF publish configuration matching object """
    pass

class RDFConfigException(Exception):
    """ RDF store binding configuration exception"""
    pass

class RDFStoreException(Exception):
    """ RDF store response exception """
    pass
    
def push_to_store(binding,  model, obj, gr ):
    from rdf4j import rdf4j_push, rdf4j_get
    from ldp import ldp_push
    """ push an object via its serialisation rules to a store via a ServiceBinding """
    if not binding:
        try:
            from rdf_io.models import ServiceBinding
            binding = ServiceBinding.get_service_bindings(model,(ServiceBinding.PERSIST_CREATE,ServiceBinding.PERSIST_UPDATE,ServiceBinding.PERSIST_REPLACE)).first()
        except:
            raise  RDFConfigNotFoundException("Cant locate appropriate repository configuration"  )
    rdfstore = { 'server_api' : binding.service_api , 'server' : binding.service_url , 'target' : binding.resource }
 
    resttgt = resolveTemplate("".join( ( rdfstore['server'],rdfstore['target'])), model, obj )   
    #import pdb; pdb.set_trace()
    if binding.service_api == "RDF4JREST" :
        return rdf4j_push(rdfstore,  model, obj, gr , binding.binding_type)
    elif binding.service_api == "LDP" :
        return ldp_push(rdfstore,  model, obj, gr ,binding_type)
    else:
        raise RDFConfigException("Unknown server API %s" % binding.service_api  )

push_to_store.RDFConfigException = RDFConfigException
push_to_store.RDFConfigNotFoundException = RDFConfigNotFoundException
push_to_store.RDFStoreException = RDFStoreException

 
def resolveTemplate(template, model, obj) :
    from rdf_io.models import getattr_path, ConfigVar
    vals = { 'model' : model }
    for (literal,param,repval,conv) in Formatter().parse(template) :
        if param and param != 'model' :
            if( param[0] == '_' ) :
                val = ConfigVar.getval(param[1:])
                if val:
                    vals[param] = val
                else:
                    raise Exception( "template references unset ConfigVariable %s" % param[1:])
            else:
                try:
                    vals[param] = iter(getattr_path(obj,param)).next()
                except:
                    if param == 'slug'  :
                        vals[param] = obj.id
    
    try:
        return template.format(**vals)
    except KeyError as e :
        raise KeyError( 'Property %s of model %s not found when creating API URL' % (e,model))

def inference(model, obj, inferencer, gr):
    """ Perform configured inferencing, return graph of new axioms
    
    use configured service binding to push an object to the inferencer, depending on its API type, perform inferencing using whatever
    rules have been set up, and return the new axioms, for disposition using the persistence rules (service bindings) for the resource """
    from rdf4j import rdf4j_push,rdf4j_get
    from ldp import ldp_push
    from rdf_io.models import ServiceBinding
    

   
#    import pdb; pdb.set_trace()
    if inferencer.service_api == "RDF4JREST" :
        rdfstore = { 'server_api' : inferencer.service_api , 'server' : inferencer.service_url ,'target' : inferencer.resource }

        rdf4j_push(rdfstore, model, obj, gr, ServiceBinding.PERSIST_REPLACE )
        rdfstore['target'] = inferencer.inferenced_resource
        inference_response = rdf4j_get( rdfstore, model, obj )
        graph = rdflib.Graph()
        newgr = graph.parse(data=inference_response.content, format='nt')
#    elif inferencer.service_api == "LDP" :
#        ldp_push(rdfstore, resttgt, model, obj, gr )
    else:
        raise RDFConfigException("Unsupported server API %s" % inferencer.service_api  )

    print "Performed inference with %s - now need to get results!" % (inferencer)
        
    return newgr 
    
def rdf_delete( binding, model, obj ):
    """ Deletes content from remote RDF store 
    
    Typically used for cleanup after inferencing and on post_delete signals for autompublished models."""
    from rdf_io.models import ServiceBinding
    print "Asked to delete from %s %s " % ( binding.service_url, binding.resource)
    return True