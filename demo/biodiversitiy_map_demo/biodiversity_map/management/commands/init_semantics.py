import os
import logging

from django.core.management.base import BaseCommand, CommandError
from django.core.management import  call_command
#~ from django.core.management.commands import loaddata

from django.conf import settings

from rdf_io.models import Namespace, ObjectType, ObjectMapping, AttributeMapping, ContentType,  ChainedMapping
from biodiversity_map.models import GeoLocation, Habitat,  Domain, Family, Genus, Organism

class Command(BaseCommand):
    """see https://docs.djangoproject.com/en/1.9/howto/custom-management-commands/ for more details
       using now new argparse mechanism of django > 1.8
    """
    logging.basicConfig(format='%(levelname)s| %(module)s.%(funcName)s:%(message)s', level=logging.DEBUG) #level=logging.ERROR

    help = 'Initialise model semantics.'

    def handle(self, *args, **options):
        #self.loaddata()

        self.load_biodiversity_semantics()

    def loaddata(self):
        """
        run loading for module
        """
        self.load_base_namespaces()
        
        return ( {'skosxl': 'loaded standard namespaces and SKOSXL object mappings'} )
        
    def load_base_namespaces(self):
        """
            load namespaces for the meta model
        """
        Namespace.objects.get_or_create( uri='http://www.w3.org/1999/02/22-rdf-syntax-ns#', defaults = { 'prefix' : 'rdf' , 'notes': 'RDF' } )
        Namespace.objects.get_or_create( uri='http://www.w3.org/2000/01/rdf-schema#', defaults = { 'prefix' : 'rdfs' , 'notes': 'RDFS' } )
        Namespace.objects.get_or_create( uri='http://www.w3.org/2004/02/skos/core#', defaults = { 'prefix' : 'skos' , 'notes': 'SKOS' } )
        Namespace.objects.get_or_create( uri='http://www.w3.org/2008/05/skos-xl#', defaults = { 'prefix' : 'skosxl' , 'notes': 'SKOSXL' } )
        Namespace.objects.get_or_create( uri='http://xmlns.com/foaf/0.1/', defaults = { 'prefix' : 'foaf' , 'notes': 'FOAF' } )
        Namespace.objects.get_or_create( uri='http://purl.org/dc/terms/', defaults = { 'prefix' : 'dct' , 'notes': 'Dublin Core Terms' } )
        Namespace.objects.get_or_create( uri='http://purl.org/dc/elements/1.1/', defaults = { 'prefix' : 'dc' , 'notes': 'Dublin Core Elements' } ) 
        Namespace.objects.get_or_create( uri='http://www.w3.org/ns/dcat#', defaults = { 'prefix' : 'dcat' , 'notes': 'DCAT' } )
        Namespace.objects.get_or_create( uri='http://www.w3.org/2001/XMLSchema#', defaults = { 'prefix' : 'xsd' , 'notes': 'XSD' } )
        Namespace.objects.get_or_create( uri='http://www.w3.org/2002/07/owl#', defaults = { 'prefix' : 'owl' , 'notes': 'OWL' } )
        

    def load_biodiversity_semantics(self):
        """ """
        logging.debug("init semantics ... ")

        #(object_type,created) = ObjectType.objects.get_or_create(uri="skos:ConceptScheme", defaults = { "label" : "SKOS ConceptScheme" })
        #sm = ObjectMapping.new_mapping(object_type, "skosxl:Scheme", "skosxl: SKOS ConceptScheme", "uri", "uri" , auto_push=True)
    
        # specific mapping
        #am = AttributeMapping(scope=sm, attr="definition", predicate="skos:definition", is_resource=False).save()

        # biodiversity 
        Namespace.objects.get_or_create( uri='http://some_rdf_site.org/biomodels/', defaults = { 'prefix' : 'bio' , 'notes': 'Data model for biodiversity' } )
        Namespace.objects.get_or_create( uri='http://some_rdf_site.org/data/habitats/', defaults = { 'prefix' : 'hab' , 'notes': 'Habitat data' } )

        (object_type,created) = ObjectType.objects.get_or_create(uri="bio:Habitat", defaults = { "label" : "Habitat class" })

        # !! right now use quoted syntax, like "'hab:'" - this should be fixed in future releases
        sm = ObjectMapping.new_mapping(object_type, "biodiversity_map:Habitat", "Habitats in RDF", "habitat_id", "'hab:'" , auto_push=False)
        # specific mapping
        am = AttributeMapping(scope=sm, attr="name", predicate="rdfs:label", is_resource=False).save()


