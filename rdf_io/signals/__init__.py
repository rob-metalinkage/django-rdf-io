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
    result = publish( obj, ct.name, oml) 
    logger.debug(
            "Persisting RDF for {} of type {} status {} body {}".format(obj,ct,result.status_code,result.content))
    
def setup_signals( **kwargs) :
    objtype = kwargs['instance']
    ct = ContentType.objects.get(id = objtype.content_type_id).model_class()
    signals.post_save.connect(publish_rdf, sender=ct)
    
    logger.info(
            "RDF publishing configured for model {}".format((ct)))
    
 
signals.post_save.connect(setup_signals, sender=ObjectMapping)
try: 
    for om in ObjectMapping.objects.all() :
        signals.post_save.send(ObjectMapping, instance=om )
except Exception as e:
    logger.info(
            "Not able to access ObjectMappings - need to run syncdb? {}".format(e))
