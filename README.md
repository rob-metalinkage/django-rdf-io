# rdf-io

Simple RDF serialiser/deserialiser to support synching a django model with an external triple-store, and an app to manage the configuration elements needed to configure such serialisation recipes.
(why an app - because we may want to take some subset of content and push it out as RDF) 

RDF_IO has initial data that loads up common W3C namespaces and prefixes ready for use (OWL, RDF, DCAT) 

## installation

get a working copy with 
git clone https://github.com/rob-metalinkage/django-rdf-io
pip install -e (where you put it)

in your master django project:
* add 'rdf_io' to the INSTALLED_APPS  in settings.py
* add     url(r"^rdf_io/", include('rdf_io.urls')) to urls.py

## Usage
	1) Define mappings for your target models using the admin interface $SERVER/admin/rdf_io
	2) To create an online resource use $SERVER/rdf_io/to_rdf/concept/2

### Mapping syntax
Mapping is non trivial - because the elements of your model may need to extracted from related models 

mapping is from elements in a Django model to a RDF value (a URI or a literal)

source model elements may be defined using XPath-like syntax, with nesting using django filter style __, a__b .(dot) or / notation, where each element of the path may support an optional filter. 

path = (literal|element([./]element)*)

literal = "a quoted string" | 'a quoted string' | <a URI>  

element = (property|related_model_expr)([filter])?

property = a valid name of a property of a django model 

related_model_expr = model_name(\({property}\))? 

filter = (field=literal)((,| AND )field=literal)* | literal((,| OR )literal)*

Notes:
* filters on related models will be evaluated within the database using django filters, filters on property values will be performed during serialisation.

* filters on properties are a simple list of possible matches (, is the same as " OR " ) and apply to the element of the path 
  person.title['MRS','MISS','MS']  would match any title with value "MRS", "MISS", "MS"

* filters on related objects are property=value syntax. Properties use django-stlye paths - i.e. notation.namespace.prefix=skos

* if a ManyToMany field is used through an intermediary, then use the related_model_expr - and if this is a self-relation then specify the property : eg.
semrelation(origin_concept)[rel_type='1'].target_concept
 
## Status: 
alpha, functionally complete initial capability:
* TTL serialisation of a given model (for which a mapping has been registered) 
* Publishing to remote LDP service using per-model templates to define LDP resources
* Autoconfiguring of signals so that objects with mappings are published on post_ save
* syc_remote method to push all objects of list of model types (push is idempotent - safe to repeat)
* sophisticated property-chains with per-level filter options in attribute marmotta
* tested in context of geonode project under django 1.6

todo:
* implement global filters for object mappings (to limit mappings to a subset)
* set up signals and methods to delete objects from remote store
* make settings more sophisticated so default target resource patterns can be inherited from app models
* test against django 1.7+

## API

### Serialising within python

from rdf_io.views import build_rdf
from django.contrib.contenttypes.models import ContentType
from rdf_io.models import ObjectMapping

ct = ContentType.objects.get(model=model)
obj_mapping_list=ObjectMapping.objects.filter(content_type=ct)
build_rdf(gr,obj, obj_mapping_list)  returns a rdflib.Graph()
gr.serialize(format="turtle")

### Serialising using django views:

{SERVER_URL}/rdf_io/to_rdf/{model_name}/{model_id}

### Configuring an external 3-store

## Marmotta LDP
* deploy marmotta.war and configure as per Marmotta instructions
* define resource container patterns for different models

e.g.

`# RDF triplestore settings
RDFSTORE = { 
    'default' : {
        'server' : "".join((SITEURL,":8080/marmotta" )),
        'target' : "/ldp/{model}/{id}",
        },
    'scheme' : {
        'target' : "/ldp/voc/{slug}",
        },
    'concept' : {
        'target' : "/ldp/voc/{scheme__slug}/{term}",
#        'headers' : { 'Slug' : "{term}" }
        }
}        
`   

* create containers necessary for patterns (eg /ldp/voc) in the example above
* deploy reasoning rules for target models (to generate additional statements that can be inferred from the published data - this is where the power comes in)
 - see http://eagle-dev.salzburgresearch.at/reasoner/admin/about.html
 e.g.
 curl -i -H "Content-Type: text/plain" -X POST --data-binary @fixtures/skos.kwrl http://localhost:8080/marmotta/reasoner/program/skos.kwrl
 curl -i -X GET http://localhost:8080/marmotta/reasoner/program/skos.kwrl
 curl -i -X GET 
 curl -i -H "Content-Type: text/plain" -X POST --data-binary @skos.skwrl http://localhost:8080/marmotta/reasoner/program/skos.skwrl
### Operations

RDF-IO is triggered automatically when saving an object once an ObjectMapping is defined for that object type.

A bulk load to the RDF store can be achieved with /rdf_io/sync_remote/{model}(,{model})*

Note that containers need to be create in the right order - so for the SKOS example  this must be /rdf_io/sync_remote/scheme,concept


# Design Goals

* Apps could define default settings (the mappings to RDF) - and these will just be ignored if the serializer is not present. 
* When bringing in the serializer, if you wanted to be able to serialize a Class in an app for which there are no default mappings, it should be possible to define these (create a rdf_mappings.py file in the top project)
* The top project will allow either the default mappings for an app to be overridden, either as a whole or on a per-mapping basis (i.e. change or add mappings for individual attributes)
* the serialiser would be available as a stand-alone serialiser for dumpdata (and extended to be a deserialiser for loaddata) - but also able to be hooked up to post the serialized data to an external service - so my serialiser app might have a model to capture connection parameters for such services - and other app settings would be able to define connections in this model and bind different model's rdf mappings to different target services.

We have four types of apps then:
1 the master project
1 the RDF serializer utility
1 imported apps that have default RDF serializations
1 imported apps that may or may not have RDF serialisations defined in the project settings.

I suspect that this may all be a fairly common pattern - but I've only seen far more heavyweight approaches to RDF trying to fully model RDF and implement SPARQL - all I want to do is spit some stuff out into an external triple-store.

default RDF serialisations are handled by loading initial_data fixtures. RDF_IO objects are defined using natural keys to allow default mappings for modules to be loaded in any order. It may be more elegant to use settings so these defaults can be customised more easily.

Signals are registered when an ObjectMapping is defined for a model. 