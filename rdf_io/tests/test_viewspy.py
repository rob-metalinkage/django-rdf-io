from rdf_io.views import *
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, RequestFactory
from django.http import HttpRequest,HttpResponse,Http404
from django.contrib.auth.models import AnonymousUser, User
# from rdf_io.tests import ObjectMappingTestCase
from .test_mappings import SerialisationSetupTestCase

from rdf_io.signals import clear_signals

class RequestTestCase(SerialisationSetupTestCase):
    """ Test case for a view request
    
    """
    def setUp(self):
        super(RequestTestCase,self).setUp()
        self.factory = RequestFactory()
        clear_signals()
        #request = self.factory.get('/rdf_io/ctl_signals/off')

        
    def test_ttl_serialise(self):
        request = self.factory.get('/rdf_io/to_rdf/objectmapping/id/1?_format=turtle')
        request.user = AnonymousUser()
        res = to_rdfbyid( request, 'objectmapping',1)
        self.assertTrue(res.content.find(b'rdfs:label "Mappings test"') >= 0)
        
    def test_json_serialise(self):
        #import pdb; pdb.set_trace()
        request = self.factory.get('/rdf_io/to_rdf/objectmapping/id/1?_format=json')
        request.user = AnonymousUser()
        res = to_rdfbyid( request, 'objectmapping',1)
        self.assertTrue(res.content.find(b'"@value": "Mappings test"') >= 0)
    
    def test_default_ttl_serialise(self):
        request = self.factory.get('/rdf_io/to_rdf/objectmapping/id/1')
        request.user = AnonymousUser()
        res = to_rdfbyid( request, 'objectmapping',1)
        #print res.content
        self.assertTrue(res.content.find(b'rdfs:label "Mappings test"') >= 0)