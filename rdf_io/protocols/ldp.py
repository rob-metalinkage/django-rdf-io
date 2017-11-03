
import requests
from api import RDFStoreException
        
def ldp_push(rdfstore, resttgt, model, obj, gr, mode ):
    """ publish using LDP protocol """
    etag = _get_etag(resttgt)
    headers = {'Content-Type': 'text/turtle'} 
    if etag :
        headers['If-Match'] = etag
       
    for h in rdfstore.get('headers') or [] :
        headers[h] = resolveTemplate( rdfstore['headers'][h], model, obj )
    
    result = requests.put( resttgt, headers=headers , data=gr.serialize(format="turtle"), auth=rdfstore.get('auth'))
    #logger.info ( "Updating resource {} {}".format(resttgt,result.status_code) )
    if result.status_code > 400 :
#         print "Posting new resource"
#         result = requests.post( resttgt, headers=headers , data=gr.serialize(format="turtle"))
#        logger.error ( "Failed to publish resource {} {}".format(resttgt,result.status_code) )
        raise RDFStoreException("Failed to publish resource {} {} : {} ".format(resttgt,result.status_code, result.content) )
    return result 

def _get_etag(uri):
    """
        Gets the LDP Etag for a resource if it exists
    """
    # could put in cache here - but for now just issue a HEAD
    result = requests.head(uri)
    return result.headers.get('ETag')