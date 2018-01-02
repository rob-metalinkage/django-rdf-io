from rdf_io.models import *
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

class ObjectMappingTestCase(TestCase):
    """ Test case for object serialisation to rdf
    
    Creates an object mapping for an ObjectMapping object - which is a suitably complex object with nested M2M and avoid us having 
    to have dependencies on other fixtures - if all a bit recursive :-) """
    
    testmapping = None
    testobj = None
    
    def setUp(self):
        (object_type,created) = ObjectType.objects.get_or_create(uri="http://metalinkage.com.au/rdfio/ObjectMapping", defaults = { "label" : "Test RDF target type" })
        content_type = ContentType.objects.get(app_label="rdf_io",model="objectmapping")
        defaults =         { "auto_push" : False , 
          "id_attr" : "id",
          "target_uri_expr" : "http://metalinkage.com.au/test/id/",
          "content_type" : content_type
        }
        
        (pm,created) =   ObjectMapping.objects.get_or_create(name="Mappings test", defaults =defaults)
        pm.obj_type.add(object_type)  

        # run mapping over myself - i'm a suitable complex object :-)
        self.testmapping = pm
        self.testobj = pm
        am = AttributeMapping(scope=pm, attr="definition", predicate="rdfs:label", is_resource=False).save()
     
    def test_getattr_path_direct_char(self):
        vals = getattr_path(self.testobj,"id_attr")
        self.assertEqual(vals[0],"id")

    def test_getattr_path_direct_int(self):
        vals = getattr_path(self.testobj,"id")
        self.assertEqual(vals[0],1)

    def test_getattr_path_nested_FK(self):
        vals = getattr_path(self.testobj,"content_type.model")
        self.assertEqual(vals[0],"objectmapping")    
        
    def test_getattr_path_nested_M2M(self):
        vals = getattr_path(self.testobj,"obj_type.uri")
        self.assertEqual(list(vals)[0],"http://metalinkage.com.au/rdfio/ObjectMapping")

        (extraobject_type,created) = ObjectType.objects.get_or_create(uri="http://metalinkage.com.au/rdfio/ObjectMapping2", defaults = { "label" : "Test RDF target type - extra" })
        self.testobj.obj_type.add(extraobject_type) 
        vals = list(getattr_path(self.testobj,"obj_type.uri"))
        self.assertEqual(len(vals),2)
        import pdb; pdb.set_trace()
        vals = list(getattr_path(self.testobj,"obj_type[uri='http://metalinkage.com.au/rdfio/ObjectMapping'].uri"))
        self.assertEqual(len(vals),1)       