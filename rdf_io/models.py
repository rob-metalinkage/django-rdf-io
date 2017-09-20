from django.db import models
from django.conf import settings

from django.utils.translation import ugettext_lazy as _
# for django 1.7 +
from django.contrib.contenttypes.fields import GenericForeignKey
#from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
try:
    from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
except:
    from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor as ReverseSingleRelatedObjectDescriptor

import requests
import itertools
import os
import rdflib

from string import Formatter


# helpers
def getattr_path(obj,path) :
    try :
        return _getattr_related(obj,obj, path.replace('__','.').replace("/",".").split('.'))
        
    except ValueError as e:
        import traceback
#        import pdb; pdb.set_trace()
        raise ValueError("Failed to map '{}' on '{}' (cause {})".format(path, obj, e))
 
def dequote(s):
    """
    If a string has single or double quotes around it, remove them.
    todo: Make sure the pair of quotes match.
    If a matching pair of quotes is not found, return the string unchanged.
    """
    if  s.startswith(("'", '"', '<')):
        return s[1:-1]
    return s
    
def _apply_filter(val, filter,localobj, rootobj) :
    """
        Apply a simple filter to a specific property, with a list of possible values
    """
    for targetval in filter.replace(" OR ",",").split(",") :
        tval = dequote(targetval)
        if tval.startswith('^') :
            tval = getattr(rootobj,tval[1:])
        elif tval.startswith('.') :
            tval = getattr(localobj,tval[1:])
        if tval == 'None' :
            return bool(val)
        elif tval == 'NotNone' :
            return not bool(val)
        elif val == tval :
            return True
    return False

def apply_pathfilter(obj, filter_expr ):
    """
        apply a filter based on a list of path expressions  path1=a,b AND path2=c,db
    """
    and_clauses = filter_expr.split(" AND ")
    
    for clause in and_clauses:

        (path,vallist) = clause.split("=")
        if path[:-1] == '!' :
            negate = True
            path = path[0:-1]
        else:
            negate = False
        or_vals = vallist.split(",")
        # if multiple values - only one needs to match
        matched = False
        for val in getattr_path(obj,path):
            for match in or_vals :
                if match == 'None' :
                    matched = negate ^ ( not val )
                elif type(val) == bool :
                    matched = negate ^ (val == (match == 'True'))
                    break;
                else :
                    if negate ^ (val == match) :
                        matched = True
                        break
            if matched :
                # dont need to check any mor - continue with the AND loop
                break
        # did any value match?
        if not matched :
            return False
            
    return True
    
def _getattr_related(rootobj,obj, fields):
    """
        get an attribute - if multi-valued will be a list object!
        fields may include filters.  
    """
    # print obj, fields
    if not len(fields):
        return [obj]
        
    field = fields.pop(0)
    filter = None
    # try to get - then check for django 1.7+ manager for related field
    try:
        # check for lang 
        try:
            (field,langfield) = field.split('@')
            if langfield[0] in ["'" , '"'] :
                lang = langfield[1:-1]
            else:
                lang = _getattr_related(rootobj,obj, [langfield,] + fields).pop(0)
                fields = []
        except:
            lang = None
        # check for datatype ^^type
        try:
            (field,typefield) = field.split('^^')
            if typefield[0] in ["'" , '"'] :
                typeuri = typefield[1:-1]
            else:
                try:
                    typeuri = _getattr_related(rootobj,obj, [typefield,] + fields).pop(0)
                except Exception as e :
                    raise ValueError("error accessing data type field '{}' in field '{}' : {}".format(typefield, field, e) )
                #have reached end of chain and have used up field list after we hit ^^
                fields = []
        except:
            typeuri = None
        # check for filt
        # check for filter 
        if "[" in field :
            filter = field[ field.index("[") +1 : -1 ]
            field = field[0:field.index("[")]
        
        val = getattr(obj, field)
        if not val :
            return []
        # import pdb; pdb.set_trace()
        try:
            # slice the list for fields[:] to force a copy so each iteration starts from top of list in spite of pop()
            return itertools.chain(*(_getattr_related(rootobj,xx, fields[:]) for xx in val.all()))
        except Exception as e:
            pass
        if filter and not _apply_filter(val, filter, obj, rootobj) :
            return []
        if lang:
            val = "@".join((val,lang))
        elif typeuri :
            val = "^^".join((val,typeuri))
    except AttributeError:

        # import pdb; pdb.set_trace()
        filters=_makefilters(filter, obj, rootobj)
        relobjs = _get_relobjs(obj,field,filters)

        # will still throw an exception if val is not set!     
    try:
        # slice the list fo fields[:] to force a copy so each iteration starts from top of list in spite of pop()
        return itertools.chain(*(_getattr_related(rootobj,xx, fields[:]) for xx in relobjs.all()))
#        !list(itertools.chain(*([[1],[2]])))
    except:
        return _getattr_related(obj,val, fields)

def _get_relobjs(obj,field,filters):
    """Find related objects that match
    
    Could be linked using a "related_name" or as <type>_set
    
    django versions have changed this around so somewhat tricky..
    """
    # then try to find objects of this type with a foreign key property using either (name) supplied or target object type
    
    if field.endswith(")") :
        (field, relprop ) = str(field[0:-1]).split("(")
    else :
        relprop = None
                   
    try:
        reltype = ContentType.objects.get(model=field)
    except ContentType.DoesNotExist as e :
        raise ValueError("Could not locate attribute or related model '{}' in element '{}'".format(field, type(obj)) )

    # if no related_name set in related model then only one candidate and djanog creates X_set attribute we can use
    try:
        return get_attr(obj, "".join((field,"_set"))).filter(**filters)
    except:
        pass
    
    # trickier then - need to look at models of the named type
    claz = reltype.model_class()
    for prop,val in claz.__dict__.items() :
        # skip related property names if set   
        if relprop and prop != relprop :
            continue
        if relprop or type(val) is ReverseSingleRelatedObjectDescriptor and val.field.related.model == type(obj) :
            filters.update({prop:obj})
            return claz.objects.filter(**filters)        
        
def _makefilters(filter, obj, rootobj):
    """Makes a django filter syntax from provided filter
    
    allow for filter clauses with references relative to the object being serialised, the root of the path being encoded or the element in the path specifying the filter""" 
    if not filter :
        return {}
    filterclauses = dict( [fc.split("=") for fc in filter.replace(" AND ",",").split(",")])
    extrafilterclauses = {}
    for fc in filterclauses :
        fval = filterclauses[fc]
        if not fval :                            
            extrafilterclauses[ "".join((fc,"__isnull"))] = False
        elif fval == 'None' :                            
            extrafilterclauses[ "".join((fc,"__isnull"))] = True
        elif fval.startswith('^'): # property value via path from root object being serialised
            try:
                objvals = getattr_path(rootobj,fval[1:])
                if len(objvals) == 0 :
                    return [] # non null match against null source fails
                extrafilterclauses[fc] = objvals.pop()
            except Exception as e:
                raise ValueError ("Error in filter clause %s on field %s " % (fc,prop))
            
        elif fval.startswith('.'): # property value via path from current path object
            try:
                objvals = getattr_path(obj,fval[1:])
                if len(objvals) == 0 :
                    return [] # non null match against null source fails
                extrafilterclauses[fc] = objvals.pop()
            except Exception as e:
                raise ValueError ("Error in filter clause %s on field %s " % (fc,prop))
        elif fval.startswith(("'", '"', '<')) :
            extrafilterclauses[fc] = dequote(fval)
        elif not filterclauses[fc].isnumeric() :
            # look for a value
            extrafilterclauses[fc] = getattr(obj, fval)
        else:
            extrafilterclauses[fc] = fval
       
    return extrafilterclauses
   
def expand_curie(value):
    try:
        parts = value.split(":")
        if len(parts) == 2 :
            ns = Namespace.objects.get(prefix=parts[0])
            return "".join((ns.uri,parts[1]))
    except:
        pass
    return value
    
def validate_urisyntax(value):

    if value[0:4] == 'http' :
        URLValidator().__call__(value)
    else :
        parts = value.split(":")
        if len(parts) != 2 :
            raise ValidationError('invalid syntax')
        ns = Namespace.objects.get(prefix=parts[0])

class RDFConfigNotFoundException(Exception):
    """ Cannot find a RDF publish configuration matching object """
    pass

class RDFConfigException(Exception):
    """ RDF store binding configuration exception"""
    pass

class RDFStoreException(Exception):
    """ RDF store response exception """
    pass
    
def push_to_store(binding,  model, obj, gr ):
    """ push an object via its serialisation rules to a store via a ServiceBinding """
    if not binding:
        try:

            binding = ServiceBinding.get_service_binding(model,(ServiceBinding.PERSIST_CREATE,ServiceBinding.PERSIST_UPDATE,ServiceBinding.PERSIST_REPLACE))
        except:
            raise  RDFConfigNotFoundException("Cant locate appropriate repository configuration"  )
    rdfstore = { 'server_api' : binding.service_api , 'server' : binding.service_url , 'target' : binding.resource }
 
    resttgt = _resolveTemplate("".join( ( rdfstore['server'],rdfstore['target'])), model, obj )   

    if binding.service_api == "RDF4JREST" :
        return _rdf4j_push(rdfstore, resttgt, model, obj, gr )
    elif binding.service_api == "LDP" :
        return _ldp_push(rdfstore, resttgt, model, obj, gr )
    else:
        raise RDFConfigException("Unknown server API %s" % binding.service_api  )

push_to_store.RDFConfigException = RDFConfigException
push_to_store.RDFConfigNotFoundException = RDFConfigNotFoundException
push_to_store.RDFStoreException = RDFStoreException
        
def _ldp_push(rdfstore, resttgt, model, obj, gr ):
    etag = _get_etag(resttgt)
    headers = {'Content-Type': 'text/turtle'} 
    if etag :
        headers['If-Match'] = etag
       
    for h in rdfstore.get('headers') or [] :
        headers[h] = _resolveTemplate( rdfstore['headers'][h], model, obj )
    
    result = requests.put( resttgt, headers=headers , data=gr.serialize(format="turtle"), auth=rdfstore.get('auth'))
    #logger.info ( "Updating resource {} {}".format(resttgt,result.status_code) )
    if result.status_code > 400 :
#         print "Posting new resource"
#         result = requests.post( resttgt, headers=headers , data=gr.serialize(format="turtle"))
#        logger.error ( "Failed to publish resource {} {}".format(resttgt,result.status_code) )
        raise RDFStoreException("Failed to publish resource {} {} : {} ".format(resttgt,result.status_code, result.content) )
    return result 

def _get_etag(uri):
    """
        Gets the LDP Etag for a resource if it exists
    """
    # could put in cache here - but for now just issue a HEAD
    result = requests.head(uri)
    return result.headers.get('ETag')
        
def _rdf4j_push(rdfstore, resttgt, model, obj, gr ):
    #import pdb; pdb.set_trace()
    headers = {'Content-Type': 'application/x-turtle;charset=UTF-8'} 
  
    for h in rdfstore.get('headers') or [] :
        headers[h] = _resolveTemplate( rdfstore['headers'][h], model, obj )
    
    result = requests.put( resttgt, headers=headers , data=gr.serialize(format="turtle"))
#    logger.info ( "Updating resource {} {}".format(resttgt,result.status_code) )
    if result.status_code > 400 :
#         print "Posting new resource"
#         result = requests.post( resttgt, headers=headers , data=gr.serialize(format="turtle"))
#        logger.error ( "Failed to publish resource {} {}".format(resttgt,result.status_code) )
         raise RDFStoreException ("Failed to publish resource {} {}".format(resttgt,result.status_code ) )
    return result 

    
def _resolveTemplate(template, model, obj) :
    
    vals = { 'model' : model }
    for (literal,param,repval,conv) in Formatter().parse(template) :
        if param and param != 'model' :
            if( param[0] == '_' ) :
                val = ConfigVar.getval(param[1:])
                if val:
                    vals[param] = val
                else:
                    raise Exception( "template references unset ConfigVariable %s" % param[1:])
            else:
                try:
                    vals[param] = iter(getattr_path(obj,param)).next()
                except:
                    if param == 'slug'  :
                        vals[param] = obj.id
    
    return template.format(**vals)

    
class CURIE_Field(models.CharField):
    """
        Char field for URI with syntax checking for CURIE or http syntax
    """
    # validate that prefix is registered if used
    validators = [ validate_urisyntax, ]
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 200
        kwargs['help_text']=_(u'use a:b or full URI')
        super( CURIE_Field, self).__init__(*args, **kwargs)
    
class EXPR_Field(models.CharField):
    """
        Char field for expression - literal or nested atribute with syntax checking for CURIE or http syntax
    """
    literal_form=None
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 400
        kwargs['help_text']=_(u'for a literal, use "quoted" syntax, for nested attribute use syntax a.b.c')
        super( EXPR_Field, self).__init__(*args, **kwargs)


class FILTER_Field(models.CharField):
    """
        Char field for filter expression:  path=value(,value)
    """

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 400
        kwargs['help_text']=_(u'path=value, eg label__label_text="frog"')
        super( FILTER_Field, self).__init__(*args, **kwargs)
        
    
# Need natural keys so can reference in fixtures - let this be the uri

class NamespaceManager(models.Manager):
    def get_by_natural_key(self, uri):
        return self.get(uri=uri)

class Namespace(models.Model) :
    """
        defines a namespace so we can use short prefix where convenient 
    """
    objects = NamespaceManager()
    
    uri = models.CharField('uri',max_length=100, unique=True, null=False)
    prefix = models.CharField('prefix',max_length=8,unique=True,null=False)
    notes = models.TextField(_(u'change note'),blank=True)

    def natural_key(self):
        return(self.uri)
    
    def get_base_uri(self):
        return self.uri[0:-1]
    def is_hash_uri(self):
        return self.uri[-1] == '#'
        
    class Meta: 
        verbose_name = _(u'namespace')
        verbose_name_plural = _(u'namespaces')
    def __unicode__(self):
        return self.uri    

class GenericMetaPropManager(models.Manager):
    def get_by_natural_key(self, curie):
        try:
            (namespace,prop) = curie.split(":")
        except:
            pass
        return self.get(namespace__prefix=namespace, propname=prop)
        
class GenericMetaProp(models.Model) :
    """
        a metadata property that can be attached to any target model to provide extensible metadata.
        Works with the namespace object to allow short forms of metadata to be displayed
    """
    objects = GenericMetaPropManager()
    namespace = models.ForeignKey(Namespace,verbose_name=_(u'namespace'))
    propname =  models.CharField(_(u'name'),blank=False,max_length=250,editable=True)
    definition  = models.TextField(_(u'definition'), blank=True)
    def natural_key(self):
        return ":".join((self.namespace.prefix,self.propname))
    def __unicode__(self):              # __unicode__ on Python 2
        return self.natural_key() 
 
        
class ObjectTypeManager(models.Manager):
    def get_by_natural_key(self, uri):
        return self.get(uri=uri)
        
class ObjectType(models.Model):
    """
        Allows for a target object to be declared as multiple object types
        Object types may be URI or CURIEs using declared prefixes
    """
    objects = ObjectTypeManager()
    uri = CURIE_Field(_(u'URI'),blank=False,editable=True)
    label = models.CharField(_(u'Label'),blank=False,max_length=250,editable=True)
    
    def natural_key(self):
        return self.uri
    
    # check short form is registered
    def __unicode__(self):              # __unicode__ on Python 2
        return " -- ".join((self.uri,self.label ))

class ObjectMappingManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)
                
class ObjectMapping(models.Model):
    """
        Maps an instance of a model to a resource (i.e. a URI with a type declaration) 
    """
    objects = ObjectMappingManager()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    name = models.CharField(_(u'Name'),help_text=_(u'unique identifying label'),unique=True,blank=False,max_length=250,editable=True)
    auto_push = models.BooleanField(_(u'auto_push'),help_text=_(u'set this to push updates to these object to the RDF store automatically'))
    id_attr = models.CharField(_(u'ID Attribute'),help_text=_(u'for nested attribute use syntax a.b.c'),blank=False,max_length=250,editable=True)
    target_uri_expr = EXPR_Field(_(u'target namespace expression'), blank=False,editable=True)
    obj_type = models.ManyToManyField(ObjectType, help_text=_(u'set this to generate a object rdf:type X statement' ))
    filter = FILTER_Field(_(u'Filter'), null=True, blank=True ,editable=True)
    def natural_key(self):
        return self.name    
  
    def __unicode__(self):              # __unicode__ on Python 2
        return self.name 
 
 
class AttributeMapping(models.Model):
    """
        records a mapping from an object mapping that defines a relation from the object to a value using a predicate
    """
    scope = models.ForeignKey(ObjectMapping)
    attr = EXPR_Field(_(u'source attribute'),help_text=_(u'literal value or path (attribute[filter].)* with optional @element or ^^element eg locationname[language=].name@language.  filter values are empty (=not None), None, or a string value'),blank=False,editable=True)
    # filter = FILTER_Field(_(u'Filter'), null=True, blank=True,editable=True)
    predicate = CURIE_Field(_(u'predicate'),blank=False,editable=True)
    is_resource = models.BooleanField(_(u'as URI'))
    
    def __unicode__(self):
        return ( ' '.join((self.attr, self.predicate )))

class EmbeddedMapping(models.Model):
    """
        records a mapping for a complex data structure
    """
    scope = models.ForeignKey(ObjectMapping)
    attr = EXPR_Field(_(u'source attribute'),help_text=_(u'attribute - if empty nothing generated, if multivalued will be iterated over'))
    predicate = CURIE_Field(_(u'predicate'),blank=False,editable=True)
    struct = models.TextField(_(u'object structure'),max_length=2000, help_text=_(u' ";" separated list of <em>predicate</em> <em>attribute expr</em>  where attribute expr a model field or "literal" or <uri> - in future may be an embedded struct inside {} '),blank=False,editable=True)
    use_blank = models.BooleanField(_(u'embed as blank node'), default=True)
    
    def __unicode__(self):
        return ( ' '.join(('struct:',self.attr, self.predicate )))

class ConfigVar(models.Model):
    """ Sets a configuration variable for ServiceBindings templates """
    var=models.CharField(max_length=16, null=False, blank=False , verbose_name='Variable name')
    value=models.CharField(max_length=255, null=False, blank=True , verbose_name='Variable value')
    
    @staticmethod
    def getval(var):
        try:
            return ConfigVar.objects.filter(var=var).first().value
        except:
            return None

class ServiceBinding(models.Model):
    """ Binds object mappings to a RDF handling service 

        Services may perform several roles:
        * Validation
        * INFERENCE
        * Persistence
        
        Bindings may be controlled by status variables in the objects being bound - for example draft content published to a separate directory.
        
        Bindings, if present for an object, override system defaults.
        
        Services may be chained with an exception handling clause. API will provide options for choosing starting point of chain and whether to automatically follow chain or report and pause.
    """
    VALIDATION='VALIDATION'
    INFERENCE='INFERENCE'
    PERSIST_CREATE='PERSIST_CREATE'
    PERSIST_REPLACE='PERSIST_REPLACE'
    PERSIST_UPDATE='PERSIST_UPDATE'
    PERSIST_PURGE='PERSIST_PURGE'
    DEBUG_SHOW='SHOW - show encoded content or previous service errors'
    BINDING_CHOICES = (
      ( VALIDATION, 'VALIDATION - Performs validation check'),
      ( INFERENCE, 'INFERENCE - The entailed response replaces the default encoding in downstream services' ),
      ( PERSIST_CREATE, 'PERSIST_CREATE - A new resource is created only if not present in the persistence store' ),
      ( PERSIST_REPLACE, 'PERSIST_REPLACE -The resource and its properties are replaced in the persistence store' ),
      ( PERSIST_UPDATE, 'PERSIST_UPDATE - The resource and its properties are added to the persistence store' ), 
      ( PERSIST_PURGE, 'PERSIST_PURGE - The resource and its properties are deleted from the persistence store' ), 
    )
    RDF4JREST = 'RDF4JREST'
    LDP = 'LDP'
    SHACLAPI = 'SHACLAPI'
    SPARQL = 'SPARQL'
    GIT = 'GIT'
    API_CHOICES=(
        (RDF4JREST,'RDF4JREST - a.k.a Sesame'),
        (LDP,'LDP: Linked Data Platform'),
        (GIT,'GIT'),
        (SHACLAPI,'SHACL service'),
        (SPARQL,'SPARQL endpoint'),
    )
    API_TEMPLATES = { RDF4JREST : "http://localhost:8080/rdf4j-server/repositories/myrepo" }

    title = models.CharField(max_length=255, blank=False, default='' )
 
    description = models.TextField(max_length=1000, null=True, blank=True)
    binding_type=models.CharField(max_length=16,choices=BINDING_CHOICES, default=PERSIST_REPLACE, help_text='Choose the role of service')
    service_api = models.CharField(max_length=16,choices=API_CHOICES, help_text='Choose the API type of service')
    service_url = models.CharField(max_length=1000, verbose_name='service url template', help_text='Parameterised service url - {var} where var is an attribute of the object type being mapped (including django nested attributes using a__b syntax) or $model for the short model name')

    resource = models.CharField(max_length=1000, verbose_name='resource path', help_text='Parameterised path to target resource - using the target service API syntax')
    object_mapping = models.ManyToManyField(ObjectMapping, verbose_name='Object mappings service applies to')
    # use_as_default = models.BooleanField(verbose_name='Use by default', help_text='Set this flag to use this by default')

    object_filter=models.TextField(max_length=2000, verbose_name='filter expression', help_text='A (python dict) filter on the objects that this binding applies to', blank=True, null=True)
    next_service=models.ForeignKey('ServiceBinding', verbose_name='Next service', blank=True, null=True)
    on_delete_service=models.ForeignKey('ServiceBinding', related_name='on_delete',verbose_name='Deletion service', blank=True, null=True, help_text='This will be invoked on object deletion if specified, and also if the binding is "replace" - which allows for a specific pre-deletion step if not supported by the repository API natively')
    on_fail_service=models.ForeignKey('ServiceBinding', related_name='on_fail',verbose_name='On fail service', blank=True, null=True, help_text='Overrides default failure reporting')

    def __unicode__(self):
        return self.title + "(" + self.service_api + " : " + self.service_url + ")"
     
    @staticmethod 
    def get_service_binding(model,bindingtypes):
        ct = ContentType.objects.get(model=model)
        return ServiceBinding.objects.filter(object_mapping__content_type=ct, binding_type__in=bindingtypes).first()
    
class ImportedResource(models.Model):
    TYPE_RULE='RULE'
    TYPE_MODEL='CLASS'
    TYPE_INSTANCE='INSTANCE'
    TYPE_QUERY='QUERY'
    TYPE_VALIDATION='VALID'
    TYPE_CHOICES = (
      ( TYPE_RULE, 'Rule (SPIN, SHACL, SKWRL etc)'),
      ( TYPE_MODEL, 'Class model - RDFS or OWL' ),
      ( TYPE_INSTANCE, 'Instance data - SKOS etc' ),
      ( TYPE_QUERY, 'Query template - SPARQL - for future use' ),
      ( TYPE_VALIDATION, 'Validation rule - for future use' ), 
    )
       
    resource_type=models.CharField(choices=TYPE_CHOICES,max_length=10,
       help_text='Determines the post processing applied to the uploaded file')   
    target_repo=models.ForeignKey(ServiceBinding, help_text='choose binding to optional RDF repository' , null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='resources/',blank=True)
    remote = models.URLField(max_length=2000,blank=True,verbose_name='Remote RDF source URI') 
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # add per user details?
 
    
#    def clean(self):
#        import fields; pdb.set_trace()
        
    def delete(self,*args,**kwargs):
        if os.path.isfile(self.file.path):
            os.remove(self.file.path)
        if self.target_repo :
            print "TODO - delete remote resource in repo %s" % self.target_repo
        super(ImportedResource, self).delete(*args,**kwargs)
    
    def save(self,*args,**kwargs):  
        if self.target_repo :
            push_to_store(self.target_repo, 'ImportedResource', self, self.get_graph())
        super(ImportedResource, self).save(*args,**kwargs)
    
    def get_graph(self):
        graph = rdflib.Graph()
        if self.file :
            format = rdflib.util.guess_format(self.file.name)
            return  graph.parse(self.file.name,  format=format )
        elif self.remote :
            format = rdflib.util.guess_format(self.remote)
            return  graph.parse(self.remote,  format=format )
        return None
        

    
    
    
    
    
    
    