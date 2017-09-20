# rdf-io

Utilities to link Django to RDF stores and inferencers.

Why: Allows semantic data models and rules to be used to generate rich views of content, and expose standardised access and query interfaces - such as SPARQL and the Linked Data Platform.  Conversely, allow use of Django to manage content in RDF stores :-)

## Features
* RDF serializer driven by editable mapping rules
* Configureable ServiceBindings to RDF store APIs for different CRUD and inferencing tasks
* RDF source load and push to designated RDF store
* chainable inferencing support and persistence handling
* Extensible to support specific information models - such as SKOS
* Configurable metadata properties for arbitrary Django objects.
RDF_IO has initial data that loads up common W3C namespaces and prefixes ready for use (OWL, RDF, DCAT) 

## installation

get a working copy with
```
git clone https://github.com/rob-metalinkage/django-rdf-io
pip install -e (where you put it)
```
in your master django project:
* add 'rdf_io' to the INSTALLED_APPS  in settings.py
* add    ` url(r"^rdf_io/", include('rdf_io.urls'))`  to urls.py
* optionally define setting for RDFSERVER and RDFSERVER_API
* run manage.py makemigrations
* run manage.py migrate

## Automated publishing of updated to RDF
This is really only guaranteed for pushing additions and updates - deletions are not handled, although updates will tend to replace statements.

### on startup to enable (necessary after django-reload)
NB - TODO a way to force this to happen automatically - needs to happen after both RDF_IO and the target models are installed, so cant go in initialisation for either model.

`{SERVER_URL}/rdf_io/ctl_signals/sync`

### to turn on publishing for a model class
1) check Auto-push flag is checked in an ObjectMapping for that model class
2) save - should register a post_save signal for the model class

### to turn on/off  publishing for all model classes 
`{SERVER_URL}/rdf_io/ctl_signals/(on/off)`

### 


## Usage

### Optional RDF store configuration
0) Set up any target RDF stores (currently supported are the LDP API and RDF4J/Apache Sesame API) - note RDF_IO can be used to import and serialise django objects as RDF without any RDF stores, and different RDF stores can be used for different objects
1) Configure variables for use in setting up ServiceBindings to RDF stores and inferencing engines
2) Set up ServiceBindings for your target stores (via the admin interface or migrations)
3) Pre-load any static data and rules required by your reasoner (e.g. SHACL) - or set up migrations to load these using ImportedResource bound to appropriate ServiceBindings

### Basic RDF serialisation
1) Define mappings for your target models using the admin interface $SERVER/admin/rdf_io
2) To create an online resource use 
		`{SERVER_URL}/rdf_io/to_rdf/{model_name}/id/{model_id}`
		`{SERVER_URL}/rdf_io/to_rdf/{model_name}/key/{model_natural_key}`
		
### RDF publishing		
1) Configure one or more ServiceBindings and attach to the relevant ObjectMapping
2) To publish a specific object to the configured RDF store 
		`{SERVER_URL}/rdf_io/pub_rdf/{model_name}/{model_id}`
		(note that this will happen automatically on object save if an object mapping is defined)
3) To republish all objects for a set of django models
		`{SERVER_URL}/rdf_io/sync_remote/{model_name}[,{model_name}]*`

### Inferencing
Inferencing allows RDF based reasoning to generate richer views of inter-related data, and potentially derive a range of additional knowledge. This can all be done inside custom logic, but RDF_IO allows standards such as SHACL etc to be used to capture this and avoids hard-coding and hiding all these rules.

when an object is saved, any enabled inferencing ServiceBindings will be applied before saving (stores may invoke loaded rules post-save)

1) Set up a RDF Inferencer - note this may be a matter of enabling inferencing on the default store, or setting up a new store 
2) Create service bindings for inferencing - these may be chained using Next_service 
3) Make sure that the inferencing store is cleared of temporary data - using an appropriate PERSISTENCE_DELETE ServiceBinding as a final step in the chain 


		
NOTE: for the 	/rdf_io/to_rdf/{model_name}/key/{model_natural_key} to work the target model must define a manage with a get_by_natural_key method that takes a unique single term - such as a uri - note this will allow use of CURIES such as myns:myterm where the prefix is registered as a namespace in the RDF_IO space. If a CURIE is detected, then RDF_IO will try to match first as a string, then expand to a full URI and match.

### Object Mappings
Mappings to RDF are done for Django models. Each mapping consists of:
1) an identifier mapping to generate the URI for the object
2) a set of AttributeMapping elements that map a list of values to a RDF predicate
3) a set of EmbeddedMapping that map a list of values to complex object property (optionally wrapped in a blank node)
4) a filter to limit the set of objects the mapping applies to

More than one object mapping may exist for a Django model. The RDF graph is the union of all the configured Object Mapping outputs.
(Note that a ServiceBinding may be bound to a specific mapping, but the default behaviour is for this to be used to find all ServiceBindings for a gioven django modeltype - and they all get the composite graph (this may be changed to supported publishing different graphs to different RDf stores in future.)

### Mapping syntax
Mapping is non trivial - because the elements of your model may need to extracted from related models 

Mapping is from elements in a Django model to a RDF value (a URI or a literal)

source model elements may be defined using XPath-like syntax, with nesting using django filter style __, a__b .(dot) or / notation, where each element of the path may support an optional filter. 
```
path = (literal|element([./]element)*)

literal = "a quoted string" | 'a quoted string' | <a URI>  

element = (property|related_model_expr)([filter])?

property = a valid name of a property of a django model 

related_model_expr = model_name(\({property}\))? 


filter = (field(!)?=literal)((,| AND )field(!)?=literal)* | literal((,| OR )literal)*
```

Notes:
* filters on related models will be evaluated within the database using django filters, filters on property values will be performed during serialisation.

* literal values of None or NULL are treated as None or empty strings, as per Django practice.

* filters on properties are a simple list of possible matches (, is the same as " OR " ) and apply to the element of the path 
  person.title['MRS','MISS','MS']  would match any title with value "MRS", "MISS", "MS"

* filters on related objects are property=value syntax. Properties use django-stlye paths - i.e. notation.namespace.prefix=skos

* if a ManyToMany field is used through an intermediary, then use the related_model_expr - and if this is a self-relation then specify the property : eg.
semrelation(origin_concept)[rel_type='1'].target_concept
 
## Status: 
beta, functionally complete initial capability:
* TTL serialisation of a given model (for which a mapping has been registered) 
* Publishing to remote LDP service using per-model templates to define LDP resources
* Autoconfiguring of signals so that objects with mappings are published on post_ save
* syc_remote method to push all objects of list of model types (push is idempotent - safe to repeat)
* sophisticated property-chains with per-level filter options in attribute marmotta
* tested in context of geonode project under django 1.6
* tested against django 1.8.6 and 1.11

todo:
* implement global filters for object mappings (to limit mappings to a subset)
* set up signals and methods to delete objects from remote store

## API

### Serialising within python
```
from rdf_io.views import build_rdf
from django.contrib.contenttypes.models import ContentType
from rdf_io.models import ObjectMapping

ct = ContentType.objects.get(model=model)
obj_mapping_list=ObjectMapping.objects.filter(content_type=ct)
build_rdf(gr,obj, obj_mapping_list)  returns a rdflib.Graph()
gr.serialize(format="turtle")
```
### Serialising using django views:

`{SERVER_URL}/rdf_io/to_rdf/{model_name}/{model_id}`




## Deprecated 
## Marmotta LDP
* deploy marmotta.war and configure as per Marmotta instructions
* define resource container patterns for different models

e.g.

```
# RDF triplestore settings
RDFSTORE = { 
    'default' : {
        'server' : "".join((SITEURL,":8080/marmotta" )),
        # model and slug are special - slug will revert to id if not present
        'target' : "/ldp/{model}/{slug}",
        # this could be pulled from settings
        'auth' : ('admin', 'pass123')
        },
    # define special patterns for nested models
    'scheme' : {
        'target' : "/ldp/voc/{slug}",
        },
    'concept' : {
        'target' : "/ldp/voc/{scheme__slug}/{term}",
        }
}        
```   

* create containers necessary for patterns (eg /ldp/voc) in the example above
* deploy reasoning rules for target models (to generate additional statements that can be inferred from the published data - this is where the power comes in)
 - see http://eagle-dev.salzburgresearch.at/reasoner/admin/about.html
 e.g.
```
 curl -i -H "Content-Type: text/plain" -X POST --data-binary @fixtures/skos.kwrl http://localhost:8080/marmotta/reasoner/program/skos.kwrl
 curl -i -X GET http://localhost:8080/marmotta/reasoner/program/skos.kwrl
 curl -i -X GET 
 curl -i -H "Content-Type: text/plain" -X POST --data-binary @skos.skwrl http://localhost:8080/marmotta/reasoner/program/skos.skwrl
 ```
### Operations

If auto_publish is set in an Object Mapping then the RDF-IO mapping is triggered automatically when saving an object once an ObjectMapping is defined for that object type.

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
