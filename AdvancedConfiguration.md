# RDF-IO Advanced

RDF-IO supports publishing	RDF outputs to a triple-store, which can support SPARQL queries and inferencing. 

It also allows inferencing stores to be used in intermediate steps to publishing to non-inferencing stores. _(NB This may be replaced by native inferencing capabilities within the RDF-IO environment in future)_

## RDF store configuration

0. Set up any target RDF stores (currently supported are the LDP API and RDF4J/Apache Sesame API) - note RDF_IO can be used to import and serialise django objects as RDF without any RDF stores, and different RDF stores can be used for different objects
1. Configure variables for use in setting up ServiceBindings to RDF stores and inferencing engines. 
2. Set up ServiceBindings for your target stores (via the admin interface or migrations)
3. Pre-load any static data and rules required by your reasoner (e.g. SHACL) - or set up migrations to load these using ImportedResource bound to appropriate ServiceBindings

## Configure variables
/admin/ConfigVars

Publishing uses a set of configuration variables which may be scoped to different phases of publication:

1. **PUBLISH** - data is send to final destination
2. **REVIEW** - data is send to an alternative data store
3. **TEST** - not used yet 

These variables are resolved in URL templates in the ServiceBindings objects.
If scope is not set, the value will be used for all cases.
 
## Publishing to a RDF store (via API) 
	
1. Configure one or more ServiceBindings and attach to the relevant ObjectMapping (if updates to that Object are to be published to RDF store - otherwise ServiceBindings can be directly bound to individual ImportedResource objects)
  NOTE: A service binding of type VALIDATION will cause checks to be performed - and on failure will abort the service chain and invoke on_fail bindings (not yet implemented) 
  NOTE: An service binding of type INFERENCING will augment the data to be stored, but not save it. It should be chained to PERSIST binding(s).
2. To publish a specific object to the configured RDF store:
		`{SERVER_URL}/rdf_io/pub_rdf/{model_name}/{model_id}`
		(note that this will happen automatically on object save if an object mapping is defined)
3. To republish all objects for a set of django models:
		`{SERVER_URL}/rdf_io/sync_remote/{model_name}[,{model_name}]*`

				
NOTE: for the 	/rdf_io/to_rdf/{model_name}/key/{model_natural_key} to work the target model must define a manage with a get_by_natural_key method that takes a unique single term - such as a uri - note this will allow use of CURIES such as myns:myterm where the prefix is registered as a namespace in the RDF_IO space. If a CURIE is detected, then RDF_IO will try to match first as a string, then expand to a full URI and match.


### Inferencing
Inferencing allows RDF based reasoning to generate richer views of inter-related data, and potentially derive a range of additional knowledge. This can all be done inside custom logic, but RDF_IO allows standards such as SHACL etc to be used to capture this and avoids hard-coding and hiding all these rules.

when an object is saved, any enabled inferencing ServiceBindings will be applied before saving (stores may invoke loaded rules post-save)

1. Set up a RDF Inferencer - note this may be a matter of enabling inferencing on the default store, or setting up a new store. If rules cannot safely co-exist, then multiple inferencing stores may be configured.
2. Load inferencing rules to the Inferencer (optionally using ImportedResource objects and PERSIST_REPLACE service bindings) 
3. Create service bindings for inferencing - these may be chained using Next_service 
4. Make sure that the inferencing store is cleared of temporary data - using an appropriate PERSISTENCE_DELETE ServiceBinding as a final step in the chain 

NOTE: Inferencing rules may need to be more complex if a separate inferencing store is set up, but some of the data needed for inferencing resides in the main target repository. Using SPIN, this leads to constructs like:

```
			 WHERE {
				?mainrepo a service:Repo  .

				?A a skos:Concept .
				OPTIONAL { ?A skos:broader ?B . }
				OPTIONAL { ?B skos:narrower ?A }
				OPTIONAL { SERVICE ?mainrepo
						{
							OPTIONAL { ?A skos:broader ?B . }
							OPTIONAL { ?B skos:narrower ?A . }

						}
					}

```

Where `?mainrepo` is an object loaded to the inferencer to define the target data store, allowing such a rule to be reusable.