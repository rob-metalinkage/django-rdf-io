from django.conf import settings
from django.db.models import signals

from django.contrib.contenttypes.models import ContentType
from rdf_io.models import ObjectMapping
from rdf_io.views import publish

import logging
logger = logging.getLogger(__name__)

def publish_rdf( **kwargs) :
    obj = kwargs['instance']
    ct = ContentType.objects.get_for_model(obj)
    oml = ObjectMapping.objects.filter(content_type=ct)
    result = publish( obj, ct.name, oml, None) 
    logger.debug(
            "Persisting RDF for {} of type {} status {} body {}".format(obj,ct,result.status_code,result.content))
    print            "Persisting RDF for {} of type {} status {} body {}".format(obj,ct,result.status_code,result.content)
    
def setup_signals( **kwargs) :
    objmapping = kwargs['instance']
    #import pdb; pdb.set_trace()
    _setup(objmapping)

def sync_signals():
    """For each ObjectMapping force signal to be added or removed"""
    mappedObj = ObjectMapping.objects.all()
    for objmapping in mappedObj:
        _setup(objmapping)
    return "synced RDf publishing signals"
    
def _setup(objmapping) :
    try:
        if objmapping.auto_push :
            ct = ContentType.objects.get(id = objmapping.content_type_id).model_class()
            signals.post_save.connect(publish_rdf, sender=ct, dispatch_uid=str(ct.__name__))
            print "RDF publishing configured for model {}".format((ct))
            logger.info(
                "RDF publishing configured for model {}".format((ct)))
    except Exception as e:
        print "Error trying to set up auto-publish for object mapping.. %s " % e
        pass

def list_pubs():
    import pdb; pdb.set_trace()
    import weakref
    msg = []
    for receiver in signals.post_save.receivers:
        (receiver_class_name,_), receiver = receiver
        # django.contrib.contenttypes.generic.GenericForeignKey.instance_pre_init is not weakref
        if isinstance(receiver, weakref.ReferenceType):
            receiver = receiver()
        receiver = getattr(receiver, '__wraps__', receiver)
        receiver_name = getattr(receiver, '__name__', str(receiver))
        text = "%s.%s" % (receiver_class_name, receiver_name)
        if receiver_name == 'publish_rdf' :
            msg.append(text)

    return str(msg)
                    