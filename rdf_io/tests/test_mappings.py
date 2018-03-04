from rdf_io.models import *
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rdflib import Literal, URIRef, Graph, XSD

class SerialisationSetupTestCase(TestCase):
    testmapping = None
    testobj = None
    attachable = None
    
    def setUp(self):
        (object_type,created) = ObjectType.objects.get_or_create(uri="http://metalinkage.com.au/rdfio/ObjectMapping", defaults = { "label" : "Test RDF target type" })
        content_type = ContentType.objects.get(app_label="rdf_io",model="objectmapping")
        defaults =         { "auto_push" : False , 
          "id_attr" : "id",
          "target_uri_expr" : '"http://metalinkage.com.au/test/id/"',
          "content_type" : content_type
        }
        
        (pm,created) =   ObjectMapping.objects.get_or_create(name="Mappings test", defaults =defaults)
        pm.obj_type.add(object_type)  

        # run mapping over myself - i'm a suitable complex object :-)
        self.testmapping = pm
        self.testobj = pm
        # create test with absolute URI with <> 
        am = AttributeMapping(scope=pm, attr="id_attr", predicate="<http://metalinkage.com.au/rdfio/id_attr>", is_resource=False).save()
        # create test with URI with http string
        am = AttributeMapping(scope=pm, attr="id_attr", predicate="http://metalinkage.com.au/rdfio/id_attr", is_resource=False).save()
        # create test with CURIE
        ns = Namespace.objects.get_or_create(uri='http://www.w3.org/2000/01/rdf-schema#', prefix='rdfs')
        am = AttributeMapping(scope=pm, attr="name", predicate="rdfs:label", is_resource=False).save()
     
        # test with language tag
        am = AttributeMapping(scope=pm, attr="name@en", predicate="rdfs:comment", is_resource=False).save()
        
        # generic metadata properties
        ns,created = Namespace.objects.get_or_create(uri='http://example.org/', prefix='eg')
        gmp,created = GenericMetaProp.objects.get_or_create(namespace=ns, propname="metaprop")
        attachable,created = AttachedMetadata.objects.get_or_create(metaprop=gmp,value="something to change during testing")

        self.attachable = attachable

class MetaObjectsTestCase(SerialisationSetupTestCase):
    """ Tests basic object behaviours needed for RDF content handling """

    def test_make_metaprop_with_uri_from_ns(self):
        """ tests that if a uri is provided for which a namespace is registered then namespace gets set"""
        gmp,created = GenericMetaProp.objects.get_or_create(uri="http://example.org/frog")
        self.assertEqual(gmp.namespace.prefix,"eg")
        self.assertEqual(gmp.propname,"frog")

    def test_get_metaprop_with_curie(self):
        gmp = GenericMetaProp.objects.get_by_natural_key("eg:metaprop")
        self.assertEqual(gmp.namespace.prefix,"eg")
        self.assertEqual(gmp.propname,"metaprop")

    def test_get_metaprop_with_url(self):
        gmp = GenericMetaProp.objects.get_by_natural_key("http://example.org/metaprop")
        self.assertEqual(gmp.namespace.prefix,"eg")
        self.assertEqual(gmp.propname,"metaprop")
        
    def test_node_string(self):
        self.assertEqual(makenode(Graph(),"frog"),Literal("frog"))

    def test_node_string_quoted(self):
        self.assertEqual(makenode(Graph(),'"frog"'),Literal("frog"))
        
    def test_node_string_int(self):
        #import pdb; pdb.set_trace()
        self.assertEqual(makenode(Graph(),"12"),Literal("12",datatype=XSD.integer))
        
    def test_node_string_lang(self):
        self.assertEqual(makenode(Graph(),"frog@en"),Literal("frog",lang="en"))

    def test_node_string_lang_quoted(self):
        self.assertEqual(makenode(Graph(),'"frog"@en'),Literal("frog",lang="en"))
        
    def test_node_string_datatype_curie(self):
        self.assertEqual(makenode(Graph(),"12^^xsd:int"),Literal("12",datatype=XSD.integer))
    
    def test_node_string_datatype_uri(self):
        self.assertEqual(makenode(Graph(),"frog^^<http://eg.org>"),Literal("frog",datatype=URIRef('http://eg.org')) )
              

    def test_quote_string(self):
        self.assertEqual(quote('frog'), '"frog"')
        
    def test_quote_string_prequoted(self):
        self.assertEqual(quote('"frog"'), '"frog"')
    
    def test_quote_string_lang(self):
        self.assertEqual(quote('frog@en'), '"frog"@en')

    def test_quote_string_lang_prequoted(self):
        self.assertEqual(quote('"frog"@en'), '"frog"@en')
        
    def test_quote_string_datatype(self):
        self.assertEqual(quote('frog^^<http://eg.org>'), '"frog"^^<http://eg.org>')

        
class ObjectMappingTestCase(SerialisationSetupTestCase):
    """ Test case for object serialisation to rdf
    
    Creates an object mapping for an ObjectMapping object - which is a suitably complex object with nested M2M and avoid us having 
    to have dependencies on other fixtures - if all a bit recursive :-) """
    
 
 
    def test_getattr_path_direct_char(self):
        vals = getattr_path(self.testobj,"id_attr")
        self.assertEqual(vals[0],"id")

    def test_getattr_path_direct_int(self):
        vals = getattr_path(self.testobj,"id")
        self.assertEqual(vals[0],self.testobj.id)

    def test_getattr_path_nested_FK(self):
        vals = getattr_path(self.testobj,"content_type.model")
        self.assertEqual(vals[0],"objectmapping")    
        
    def test_getattr_path_nested_M2M(self):
        vals = getattr_path(self.testobj,"obj_type.uri")
        self.assertEqual(list(vals)[0],"http://metalinkage.com.au/rdfio/ObjectMapping")

    def test_getattr_path_nested_M2M_filter_on_string(self):
        (extraobject_type,created) = ObjectType.objects.get_or_create(uri="http://metalinkage.com.au/rdfio/ObjectMapping2", defaults = { "label" : "Test RDF target type - extra" })
        self.testobj.obj_type.add(extraobject_type) 
        vals = list(getattr_path(self.testobj,"obj_type.uri"))
        self.assertEqual(len(vals),2)
        vals = list(getattr_path(self.testobj,"obj_type[uri='http://metalinkage.com.au/rdfio/ObjectMapping'].uri"))
        self.assertEqual(len(vals),1)
        vals = list(getattr_path(self.testobj,"obj_type[uri='http://metalinkage.com.au/rdfio/ObjectMapping2'].uri"))
        self.assertEqual(len(vals),1)
        vals = list(getattr_path(self.testobj,"obj_type[uri='http://metalinkage.com.au/rdfio/ObjectMapping3'].uri"))
        self.assertEqual(len(vals),0)
        vals = list(getattr_path(self.testobj,"obj_type[uri!='http://metalinkage.com.au/rdfio/ObjectMapping3'].uri"))
        self.assertEqual(len(vals),2)

    def test_getattr_path_nested_M2M_filter_int(self):
        (extraobject_type,created) = ObjectType.objects.get_or_create(uri="http://metalinkage.com.au/rdfio/ObjectMapping2", defaults = { "label" : "Test RDF target type - extra" })
        self.testobj.obj_type.add(extraobject_type) 
        vals = list(getattr_path(self.testobj,"obj_type[id=%s].id" % extraobject_type.id))
        self.assertEqual(list(vals)[0],extraobject_type.id)
        # 
        vals = list(getattr_path(self.testobj,"obj_type[id!=%s].id" % extraobject_type.id))
        self.assertNotEqual(list(vals)[0],extraobject_type.id)
        
    def test_get_relobjs(self):
        """ test case where related objects refer to this object (reverse FK)  """
        #import pdb; pdb.set_trace()
        relobjs = list(getattr_path(self.testmapping,'attributemapping'))
        self.assertEqual(len(relobjs),4)
        
        