
import requests
from api import RDFStoreException, resolveTemplate

       
def rdf4j_push(rdfstore, model, obj, gr, mode ):
    #import pdb; pdb.set_trace()
    from rdf_io.models import ServiceBinding
    headers = {'Content-Type': 'application/x-turtle;charset=UTF-8'} 
    
    resttgt = resolveTemplate("".join( ( rdfstore['server'],rdfstore['target'])), model, obj )
    for h in rdfstore.get('headers') or [] :
        headers[h] = resolveTemplate( rdfstore['headers'][h], model, obj )
    
    if mode == ServiceBinding.PERSIST_REPLACE :
        result = requests.put( resttgt, headers=headers , data=gr.serialize(format="turtle"))
    elif mode == ServiceBinding.PERSIST_UPDATE :
        result = requests.post( resttgt, headers=headers , data=gr.serialize(format="turtle"))
    elif mode == ServiceBinding.PERSIST_DELETE :
        result = requests.delete( resttgt, headers=headers )
    else:
        raise Exception ("RDF4J store does not yet support mode %s" % (mode,))
#    logger.info ( "Updating resource {} {}".format(resttgt,result.status_code) )
    if result.status_code > 400 :
#         print "Posting new resource"
#         result = requests.post( resttgt, headers=headers , data=gr.serialize(format="turtle"))
#        logger.error ( "Failed to publish resource {} {}".format(resttgt,result.status_code) )
         raise RDFStoreException ("Failed to publish resource {} {}".format(resttgt,result.status_code ) )
    return result 

def rdf4j_get(rdfstore, model,obj):    
    """ Gets a response from an RDF4J datastore access method. Returns HTTP request
    
    """
    headers = {'Content-Type': 'application/x-turtle;charset=UTF-8'} 
    
    resttgt = resolveTemplate("".join( ( rdfstore['server'],rdfstore['target'])), model, obj )
    result = requests.get( resttgt, headers=headers )
    return result

def rdf4j_delete(rdfstore, model,obj):    
    """ Gets a response from an RDF4J datastore access method. Returns HTTP request
    
    """
    headers = {'Content-Type': 'application/x-turtle;charset=UTF-8'} 
    
    resttgt = resolveTemplate("".join( ( rdfstore['server'],rdfstore['target'])), model, obj )
    result = requests.delete( resttgt, headers=headers )
    return result    