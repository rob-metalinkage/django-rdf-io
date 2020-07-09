biodiversity_map demo
=====================

Introduction / motivation
--------------------------

The biodiversity_map demo shall illustrate a very concrete example, how django-rdf-io can be used and mapping to external 
ontologies can be achieved. 
django is used to collect information about an organism and to geographical location in a relational database.
The tables of the relational database do contain semantic information a priory, which means that computer cannot understand what 
the meaning of the database table "habitat" is and how to interpret the columns of this table. 
By mapping the database table to ontologies it is possible to add this missing information which results e.g. 
in the application of very powerful data query and aggregation tools like SPARQL and semantic web technologies.
This tools allow connecting your local biodiversity database with worldwide distributed databases providing enrichment of your 
local data with data from the wold wide web.
Since the django databases cannot be directly addressed by SPARQL query language, django-rdf-io was developed to push
automatically (if configured) rdf mappings of database models and attributes to a graph database utilising the LDP or rdf4j api 
and keeping the graph databes up to date.

The biodiversity_map demo example combines geographical information, information about habitas and information about a biological species (taxonomy).

General workflow:
1. specfiy your models
1. add the mappings
   - mappings can be adde by the admin back-end s. $SERVER/admin/rdf_io 
   - they can also added by calling urls: 
      in the browser address field enter
       {SERVER_URL}/rdf_io/to_rdf/{model_name}/id/{model_id}
       e.g. 
       my_biodiv_server.org/rdf_io/to_rdf/habitat/id/{model_id}
       or via key: 
       {SERVER_URL}/rdf_io/to_rdf/{model_name}/key/{model_natural_key} 

    [@Rob] could you please add some mapping concrete examples, applying the mapping syntax ?

   - mappings can also added to the model as shown in biodiversity_map/models.py
1. push rdfs to graph database / SPARQLendpoint or activate automatic graph database update


Installation
-------------

Requirements to run the demo
 - django > 3.0
 - python > 3.6
 - an installed instance of a graph databse with Linded Data Protocol (LDP) support, like virtuoso, ...
   alternatively: a running instance of rdf4j

1. install django-rdf-io as described in the django-rdf-io README.
1. additionally install django-skosxl as described there, since it is highly recommended to use the 
   [SKOS data model](https://www.w3.org/TR/skos-reference/) to describe relations between your data model and external ontologies.
1. the connection parameters to the graph database are set in $SERVER/admin/rdf_io/configVar

Usage / running the demo
--------------------------

  cd biodiversity_map
  python3 mange.py makemigrations biodiversity_map
  python3 mange.py migrate
  python3 mange.py runserver
  
  # now visit localhost:8000/admin in your browser and add the mappings in the rdf-io section

  # to retrive some rdfs manually, just ender a url to a model id in the address line of your browser, like e.g.
   my_biodiv_server.org/rdf_io/to_rdf/habitat/id/1 


