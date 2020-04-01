from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
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
import sys
import re
import requests
import itertools
import os
from rdflib import Graph,namespace, XSD
from rdflib.term import URIRef, Literal
from six import string_types
from rdflib.namespace import NamespaceManager,RDF
from rdf_io.protocols import *
from django.db.models import Q

# helpers
def getattr_path(obj,path) :
    """ Get a list of attribute values matching a nested attribute path with filters 
    
    format of path is a string  a.b.c  with optional filters a[condition].b[condition] etc
    """
    try :
        return _getattr_related(obj,obj, pathsplit(path.replace('__','.')), extravals={})
        
    except ValueError as e:
        import traceback
#        import pdb; pdb.set_trace()
        raise ValueError("Failed to map '{}' on '{}' (cause {})".format(path, obj, e))

def pathsplit(str):
    """ takes a path with filters which may include literals, and ignores filter contents when splitting """
    result = []
    tok_start = 0
    infilt= False
    for i,c in enumerate(str) :
        if c == '.' and not infilt :
            result.append( str[tok_start:i])
            tok_start = i+1
        elif c == '[' :
            infilt=True
        elif c == ']' :
            infilt=False
    result.append(str[tok_start:])
    return result
    
def getattr_tuple_path(obj,pathlist) :
    """ Get a list of attribute value tuples matching a set of nested attribute paths with filters 
    
    format of each path is a string  a.b.c  with optional filters a[condition].b[condition] etc
    
    tuples are generated at the level of common path - e.g (a.b.c,a.b.d) generaters the tuple (val(c), val(d)) for objects in path a.b
    """ 
    for p in pathlist:
        p.replace('__','.').replace("/",".")
    try :
        return _getattr_related(obj,obj, pathsplit(pathlist[0]), pathlist=pathlist[1:], extravals={})
        
    except ValueError as e:
        import traceback
#        import pdb; pdb.set_trace()
        raise ValueError("Failed to map '{}' on '{}' (cause {})".format(pathlist, obj, e))
        
def dequote(s):
    """ Remove outer quotes from string 
    
    If a string has single or double quotes around it, remove them.
    todo: Make sure the pair of quotes match.
    If a matching pair of quotes is not found, return the string unchanged.
    """
    if s.startswith('"""') :
        return s[3:-3]
    elif  s.startswith(("'", '"', '<')):
        return s[1:-1]
    return s

def quote(s):
    """ quote string so it gets processed as a literal
    
    leave @lang and ^^datatype qualifiers outside quoting!
    """
    
    if  isinstance(s, string_types) and s[0] not in ('"',"'"):
        try:
            root,lang = s.split('@')
            return ''.join(('"',root,'"','@',lang))
        except:
            try:
                root,lang = s.split('^^')
                return ''.join(('"',root,'"','^^',lang))
            except:            
                return s.join(('"','"'))
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
    """ does obj match filter expression?
    
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
                    if negate ^ (val == dequote(match)) :
                        matched = True
                        break
            if matched :
                # dont need to check any mor - continue with the AND loop
                break
        # did any value match?
        if not matched :
            return False
            
    return True
    
def _getattr_related(rootobj,obj, fields, pathlist=None, extravals={} ):
    """ recursive walk down object path looking for field values 
    
        get an attribute - if multi-valued will be a list object!
        if pathlist is present, then each path in the 
        fields may include filters.  
    """
    # print obj, fields
    if not len(fields):
        return [[obj,] + [ extravals[i] for i in range(0,len(extravals)) ]] if extravals else [obj]
        
    field = fields.pop(0)
    if pathlist:
        pathlist2= list(pathlist)
        for i,p in enumerate(pathlist):
            if not p :
                continue
            elif p.startswith(field + "."):
                pathlist2[i] = p[len(field)+1:]
            else :
                pathlist2[i] = None
                extravals[i] = getattr_path(obj,p)
        pathlist = tuple(pathlist2)
    filter = None
    filters = None
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
            filters=_makefilters(filter, obj, rootobj)

        val = getattr(obj, field)
        if not val :
            return []
        # import pdb; pdb.set_trace()
        try:
            # slice the list for fields[:] to force a copy so each iteration starts from top of list in spite of pop()
            if filter:
                valset = val.filter(**filters['includes']).exclude(**filters['excludes'])
            else :
                valset = val.all()
            return itertools.chain(*(_getattr_related(rootobj,xx, fields[:], pathlist=pathlist,extravals=extravals) for xx in valset))
        except Exception as e:
            pass
        if filter and not _apply_filter(val, filter, obj, rootobj) :
            return []
        if lang:
            val = "@".join((val,lang))
        elif typeuri :
            val = "^^".join((val,typeuri))
    except AttributeError:
        relobjs = _get_relobjs(obj,field,filters)

        # will still throw an exception if val is not set!     
    try:
        # slice the list fo fields[:] to force a copy so each iteration starts from top of list in spite of pop()
        return itertools.chain(*(_getattr_related(rootobj,xx, fields[:], pathlist=pathlist) for xx in relobjs.all()))
#        !list(itertools.chain(*([[1],[2]])))
    except:
        try:
            return _getattr_related(obj,val, fields, pathlist=pathlist,extravals=extravals)
        except:
            raise ValueError( "Object type %s has no related model %s " % ( str(type(obj)), str(fields) ))

def _get_relobjs(obj,field,filters=None):
    """Find related objects that match
    
    Could be linked using a "related_name" or as <type>_set
    
    django versions have changed this around so somewhat tricky..
    """
    # then try to find objects of this type with a foreign key property using either (name) supplied or target object type
    
    if not filters:
        filters = { 'includes': {} , 'excludes' : {} }
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
        return getattr(obj, "".join((field,"_set"))).filter(**filters['includes']).exclude(**filters['excludes'])
    except:
        pass
    
    # trickier then - need to look at models of the named type
    claz = reltype.model_class()
    for prop,val in claz.__dict__.items() :
        # skip related property names if set   
        if relprop and prop != relprop :
            continue
        if relprop or type(val) is ReverseSingleRelatedObjectDescriptor and val.field.related.model == type(obj) :
            filters['includes'].update({prop:obj})
            return claz.objects.filter(**filters['includes']).exclude(**filters['excludes'])        
        
def _makefilters(filter, obj, rootobj):
    """Makes a django filter syntax for includes and excludes from provided filter
    
    allow for filter clauses with references relative to the object being serialised, the root of the path being encoded or the element in the path specifying the filter""" 
    if not filter :
        return {}
    filterclauses = dict( [fc.split("=") for fc in filter.replace(" AND ",",").split(",")])
    includes = {}
    excludes = {}
    for fc in filterclauses :
        fval = filterclauses[fc]
        if fc[-1] == '!' :
            excludes = _add_clause(excludes, fc[0:-1], fval, obj, rootobj)
        else:
            includes = _add_clause(includes, fc, fval, obj, rootobj)

    return { 'includes': includes , 'excludes' : excludes }        
            
def _add_clause(extrafilterclauses, fc, fval , obj, rootobj):
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
    elif not unicode(fval).isnumeric() :
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

def as_uri(value):
    """ puts <> around if not a CURIE """
    try:
        parts = value.split(":")
        if len(parts) == 2 :
			return value
    except:
        pass
    return value.join("<",">")
    

def as_resource(gr,curie) :
    cleaned = dequote(curie)
    if cleaned[0:4] == 'http' :
        return URIRef(cleaned)
    # this will raise error if not valid curie format
    try:
        (ns,value) = cleaned.split(":",2)
    except:
        return URIRef(cleaned)  # just have to assume its not a problem - URNs are valid uri.s
        # raise ValueError("value not value HTTP or CURIE format %s" % curie)    
    try :
        nsuri = Namespace.getNamespace(ns)
        if nsuri :
            gr.namespace_manager.bind( str(ns), namespace.Namespace(nsuri), override=False)
            return URIRef("".join((str(nsuri),value)))
        else :
            return URIRef(cleaned) 
    except:
        raise ValueError("prefix " + ns + "not recognised")

TYPES = { 
    'xsd:int' : XSD.integer ,
    'xsd:float': XSD.float , 
    'xsd:double': XSD.double , 
    'xsd:time' : XSD.time ,
    'xsd:dateTime' : XSD.dateTime ,
    'xsd:boolean' : XSD.boolean ,
    'xsd:integer' : XSD.integer ,
    }
    
def makenode(gr,value, is_resource=False):
    """ make a RDF node from a string representation
    
    probably ought to be able to find this function in rdflib but seems hidden"""
    if is_resource or value[0] == '<' and '<' not in value[1:] and value [-1] == '>' :
        return as_resource(gr,value)
    else:
        try:
            try :
                (value,valtype) = value.split("^^")
                try:
                    typeuri = TYPES[valtype]
                except:
                    typeuri = as_resource(gr,valtype)
                return Literal(dequote(value),datatype=typeuri)
            except:
                try :
                    (value,valtype) = value.split("@")
                    return Literal(dequote(value),lang=valtype)
                except:
                    try:
                        value = int(value)
                        return Literal(value, datatype=XSD.integer)
                    except:
                        try:
                            value = double(value)
                            return Literal(value, datatype=XSD.double)
                        except:
                            return Literal(dequote(value))
        except:
            raise ValueError("Value not a convertable type %s" % type(value))        
 
    
def validate_urisyntax(value):

    if value[0:4] == 'http' :
        URLValidator().__call__(value)
    else :
        parts = value.split(":")
        if len(parts) != 2 :
            raise ValidationError('invalid syntax - neither http URI or a valid CURIE')
#        try:
#            ns = Namespace.objects.get(prefix=parts[0])
#        except Exception as e:
#            raise ValidationError("Namespace not defined for prefix %s" % parts[0])

def validate_propertypath(path):
    for value in path.split():
        validate_urisyntax(value)

    
class RDFpath_Field(models.CharField):
    """
        Char field for URI with syntax checking for CURIE or http syntax
    """
    # validate that prefix is registered if used
    validators = [ validate_propertypath, ]
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 500
        kwargs['help_text']=_(u'space separated list of RDF property URIs (in form a:b or full URI) representing a nested set of properties in an RDF graph')
        super( RDFpath_Field, self).__init__(*args, **kwargs)
        
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
        return(self.uri,)
    
    def get_base_uri(self):
        return self.uri[0:-1]
    def is_hash_uri(self):
        return self.uri[-1] == '#'
    
    @staticmethod
    def getNamespace( prefix) :
        try:
            return Namespace.objects.get(prefix = prefix)
        except:
            return None
      
    class Meta: 
        verbose_name = _(u'namespace')
        verbose_name_plural = _(u'namespaces')
    def __unicode__(self):
        return self.uri    

class GenericMetaPropManager(models.Manager):
    def get_by_natural_key(self, curie):
        try:
            (namespace,prop) = curie.split(":")
            return self.get(namespace__prefix=namespace, propname=prop)
        except:
            return self.get(uri=curie)
            
        
class GenericMetaProp(models.Model) :
    """
        a metadata property that can be attached to any target model to provide extensible metadata.
        Works with the namespace object to allow short forms of metadata to be displayed
    """
    objects = GenericMetaPropManager()
    namespace = models.ForeignKey(Namespace,blank=True, null=True, verbose_name=_(u'namespace'))
    propname =  models.CharField(_(u'name'),blank=True,max_length=250,editable=True)
    uri = CURIE_Field(blank=True, unique=True)
    definition  = models.TextField(_(u'definition'), blank=True)
    def natural_key(self):
        return  ( ":".join((self.namespace.prefix,self.propname)) if self.namespace else self.uri , )
    def __unicode__(self):              # __unicode__ on Python 2
        return self.natural_key()[0]
    def asURI(self):
        """ Returns fully qualified uri form of property """
        return uri
        
    def save(self,*args,**kwargs):
        if self.namespace :
            self.uri = "".join((self.namespace.uri,self.propname))
        else:
            try:
                (dummy, base, sep, term) = re.split('(.*)([/#])', self.uri)
                ns = Namespace.objects.get(uri="".join((base,sep)))
                if ns:
                    self.namespace = ns
                    self.propname = term
            except:
                pass
                
        super(GenericMetaProp, self).save(*args,**kwargs)


class AttachedMetadata(models.Model):
    """ metadata property that can be attached using subclass that specificies the subject property FK bining 
    
        extensible metadata using rdf_io managed reusable generic metadata properties
    """
    metaprop   =  models.ForeignKey(GenericMetaProp,verbose_name='property') 
    value = models.CharField(_(u'value'),max_length=2000)
    def __unicode__(self):
        return unicode(self.metaprop.__unicode__())   
    def getRDFValue(self):
        """ returns value in appropriate datatype """
        return makenode(value)

    class Meta:
        pass
 #       abstract = True        
        
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
        return (self.uri,)
    
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
        return (self.name,)    
  
    def __unicode__(self):              # __unicode__ on Python 2
        return self.name 
 
    @staticmethod
    def new_mapping(object_type,content_type_label, title, idfield, tgt,filter=None, auto_push=False, app_label=None):
        if not app_label :
            try:
                (app_label,content_type_label) = content_type_label.split(':')
            except:
                pass # hope we can find it?
        content_type = ContentType.objects.get(app_label=app_label.lower(),model=content_type_label.lower())
        defaults =         { "auto_push" : auto_push , 
              "id_attr" : idfield,
              "target_uri_expr" : tgt,
              "content_type" : content_type
            }
        if filter :
            defaults['filter']=filter
            
        (pm,created) =   ObjectMapping.objects.get_or_create(name=title, defaults =defaults)
        if not created :
            AttributeMapping.objects.filter(scope=pm).delete()
        
        pm.obj_type.add(object_type)
        pm.save()    

        return pm   
 
 
class AttributeMapping(models.Model):
    """
        records a mapping from an object mapping that defines a relation from the object to a value using a predicate
    """
    scope = models.ForeignKey(ObjectMapping)
    attr = EXPR_Field(_(u'source attribute'),help_text=_(u'literal value or path (attribute[filter].)* with optional @element or ^^element eg locationname[language=].name@language.  filter values are empty (=not None), None, or a string value'),blank=False,editable=True)
    # filter = FILTER_Field(_(u'Filter'), null=True, blank=True,editable=True)
    predicate = CURIE_Field(_(u'predicate'),blank=False,editable=True,help_text=_(u'URI or CURIE. Use :prop.prop.prop form to select a property of the mapped object to use as the predicate'))
    is_resource = models.BooleanField(_(u'as URI'))
    
    def __unicode__(self):
        return ( ' '.join((self.attr, self.predicate )))

class EmbeddedMapping(models.Model):
    """ embedded mapping using a template
    
        records a mapping for a complex data structure
    """
    scope = models.ForeignKey(ObjectMapping)
    attr = EXPR_Field(_(u'source attribute'),help_text=_(u'attribute - if empty nothing generated, if multivalued will be iterated over'))
    predicate = CURIE_Field(_(u'predicate'),blank=False,editable=True, help_text=_(u'URI or CURIE. Use :prop.prop.prop form to select a property of the mapped object to use asthe predicate'))
    struct = models.TextField(_(u'object structure'),max_length=2000, help_text=_(u' ";" separated list of <em>predicate</em> <em>attribute expr</em>  where attribute expr a model field or "literal" or <uri> - in future may be an embedded struct inside {} '),blank=False,editable=True)
    use_blank = models.BooleanField(_(u'embed as blank node'), default=True)
    
    def __unicode__(self):
        return ( ' '.join(('struct:',self.attr, self.predicate )))

class ChainedMapping(models.Model):
    """ nested mapping using another mapping
    
        Chains to a specific mapping to nest the resulting graph within the current serialisation
    """
    scope = models.ForeignKey(ObjectMapping,editable=False, )
    attr = EXPR_Field(_(u'source attribute'),help_text=_(u'attribute - if empty nothing generated, if multivalued will be iterated over'))
    predicate = CURIE_Field(_(u'predicate'),blank=False,editable=True, help_text=_(u'URI or CURIE. Use :prop.prop.prop form to select a property of the mapped object to use asthe predicate'))
    chainedMapping = models.ForeignKey(ObjectMapping, blank=False,editable=True, related_name='chained',help_text=_(u'Mapping to nest, for each value of attribute. may be recursive'))
    
    def __unicode__(self):
        return ( ' '.join(('chained mapping:',self.attr, self.predicate, self.chainedMapping.name )))
 
MODE_CHOICES = (
      ( 'REVIEW', 'Persist results in mode for review'),
      ( 'TEST', 'Does not persist results' ),
      ( 'PUBLISH' , 'Data published to final target' )
    )
    
class ConfigVar(models.Model):
    
    """ Sets a configuration variable for ServiceBindings templates """
    var=models.CharField(max_length=16, null=False, blank=False , verbose_name='Variable name')
    value=models.CharField(max_length=255, null=False, blank=True , verbose_name='Variable value')
    mode=models.CharField( verbose_name='Mode scope', choices=MODE_CHOICES,null=True,blank=True,max_length=10 )
    
    def __unicode__(self):
        return ( ' '.join(('var:',self.var, ' (', str(self.mode), ') = ', self.value )))
    
    @staticmethod
    def getval(var,mode):
        try:
            return ConfigVar.objects.filter(var=var, mode=mode).first().value
        except:
            try:
                return ConfigVar.objects.filter(var=var, mode__isnull=True).first().value
            except: 
                pass
        return None
        
    @staticmethod
    def getvars(mode):
        return ConfigVar.objects.filter(Q(mode=mode) | Q(mode__isnull=True)).order_by('var')
        

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
      ( PERSIST_REPLACE, 'PERSIST_REPLACE - (e.g. HTTP PUT) The resource and its properties are replaced in the persistence store' ),
      ( PERSIST_UPDATE, 'PERSIST_UPDATE - (e.g. HTTP POST) The resource and its properties are added to the persistence store' ), 
      ( PERSIST_PURGE, 'PERSIST_PURGE - (e.g. HTTP DELETE) The resource and its properties are deleted from the persistence store' ), 
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

    resource = models.CharField(max_length=1000, verbose_name='resource path', help_text='Parameterised path to target resource to be persisted - using the target service API syntax - e.g. /statements?context=<{uri}> for a RDF4J named graph.', default="/statements?context=<uri>")
    inferenced_resource = models.CharField(max_length=1000, verbose_name='generated resource', help_text='Parameterised path to intermediate resource - using the target service API syntax.  If this is an inferencing service then this will be the resource identifier for the additional triples generated by the inferencing rules generated for the specific object.', null=True,blank=True)
    object_mapping = models.ManyToManyField(ObjectMapping, verbose_name='Object mappings service binding applies to automatically', blank=True)
    # use_as_default = models.BooleanField(verbose_name='Use by default', help_text='Set this flag to use this by default')

    object_filter=models.TextField(max_length=2000, verbose_name='filter expression', help_text='A (python dict) filter on the objects that this binding applies to', blank=True, null=True)
    next_service=models.ForeignKey('ServiceBinding', verbose_name='Next service', blank=True, null=True)
    on_delete_service=models.ForeignKey('ServiceBinding', related_name='on_delete',verbose_name='Deletion service', blank=True, null=True, help_text='This will be invoked on object deletion if specified, and also if the binding is "replace" - which allows for a specific pre-deletion step if not supported by the repository API natively')
    on_fail_service=models.ForeignKey('ServiceBinding', related_name='on_fail',verbose_name='On fail service', blank=True, null=True, help_text='Overrides default failure reporting')

    def __unicode__(self):
        return self.title + "(" + self.service_api + " : " + self.service_url + ")"
     
    @staticmethod 
    def get_service_bindings(model,bindingtypes):
        ct = ContentType.objects.get(model=model)
        if bindingtypes:
            return ServiceBinding.objects.filter(object_mapping__content_type=ct, binding_type__in=bindingtypes)
        else:
            return ServiceBinding.objects.filter(object_mapping__content_type=ct)

class ResourceMeta(AttachedMetadata):
    """
        extensible metadata using rdf_io managed reusable generic metadata properties
    """
    subject       = models.ForeignKey("ImportedResource", related_name="metaprops")  
    
@python_2_unicode_compatible              
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
    
    savedgraph = None
    
    subtype = models.ForeignKey(ContentType,editable=False,null=True,verbose_name='Specific Type')
    
    resource_type=models.CharField(choices=TYPE_CHOICES,default=TYPE_INSTANCE,max_length=10,
    help_text='Determines the post processing applied to the uploaded file')   
    target_repo=models.ForeignKey(ServiceBinding, verbose_name='Data disposition',help_text='This is a service binding for the data object, in addition to any service bindings applied to the Imported Resource metadata.' , null=True, blank=True)
    description = models.CharField(verbose_name='ImportedResource Name',max_length=255, blank=True)
    file = models.FileField(upload_to='resources/',blank=True)
    remote = models.URLField(max_length=2000,blank=True,verbose_name='Remote RDF source URI') 
    graph = models.URLField(max_length=2000,blank=True,null=True,verbose_name='Target RDF graph name') 
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # add per user details?
 
    def __unicode__(self):
        return ( ' '.join( filter(None,(self.resource_type,':', self.file.__unicode__(), self.remote ))))
 
    def __str__(self):
        return ( ' '.join( filter(None,(self.resource_type,':', self.file.__unicode__(), self.remote ))))
        
#    def clean(self):
#        import fields; pdb.set_trace()
        
    def delete(self,*args,**kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        if self.target_repo :
            print "TODO - delete remote resource in repo %s" % self.target_repo
        super(ImportedResource, self).delete(*args,**kwargs)
    
    def save(self,*args,**kwargs): 
        #import pdb; pdb.set_trace()
        if(not self.subtype):
            self.subtype = ContentType.objects.get_for_model(self.__class__)
        if not self.description:
            self.description = self.__unicode__()
        super(ImportedResource, self).save(*args,**kwargs)
        # service binding to push original content
        if self.target_repo :
            push_to_store(self.target_repo, 'ImportedResource', self, self.get_graph(), mode='PUBLISH')
        oml = ObjectMapping.objects.filter(content_type__model='importedresource')
        if oml :
            publish( self, 'importedresource', oml)
    
    def get_graph(self):
        # import pdb; pdb.set_trace()
        if self.savedgraph :
            pass # just return it
        elif self.file :
            format = rdflib.util.guess_format(self.file.name)
            self.savedgraph = rdflib.Graph().parse(self.file.name,  format=format )
        elif self.remote :
            format = rdflib.util.guess_format(self.remote)
            self.savedgraph = rdflib.Graph().parse(self.remote,  format=format )
        return self.savedgraph
        
    def getPathVal(self,gr,rootsubject,path):
        
        els = path.split()
        nels = len(els)
        idx = 1
		
        sparql="SELECT DISTINCT ?p_%s WHERE { <%s> %s ?p_%s ." % (nels,str(rootsubject), as_uri(els[0]), str(idx)) 
        while idx < nels :
            sparql +=  " ?p_%s %s ?p_%s ." % (str(idx), as_uri(els[idx]), str(idx+1)) 
            idx += 1
        sparql += " } "
#        print sparql
        results = gr.query(sparql)
        # check if a literal now!
        for res in results:
            return res[0]
    
def publish(obj, model, oml, rdfstore=None , mode='PUBLISH'):
      
       
    gr = Graph()
    #import pdb; pdb.set_trace()
#    ns_mgr = NamespaceManager(Graph())
#    gr.namespace_manager = ns_mgr
    try:
        gr = build_rdf(gr, obj, oml, True)
        if not gr:
            return []
    except Exception as e:
        print(sys.exc_info()[0])
        raise Exception("Error during serialisation: " + str(e) )
   
#    curl -X POST -H "Content-Type: text/turtle" -d @- http://192.168.56.151:8080/marmotta/import/upload?context=http://mapstory.org/def/featuretypes/gazetteer 
    
    inference_chain_results = []
    for next_binding in ServiceBinding.get_service_bindings(model,None) :
        newgr = gr  # start off with original RDF graph for each new chain
        while next_binding :
            print ( next_binding.__unicode__() )
            if next_binding.binding_type == ServiceBinding.INFERENCE :
                newgr = inference(model, obj, next_binding, newgr, mode)
            elif next_binding.binding_type in ( ServiceBinding.PERSIST_UPDATE, ServiceBinding.PERSIST_REPLACE, ServiceBinding.PERSIST_CREATE ) :
                push_to_store( next_binding, model, obj, newgr , mode)
            elif next_binding.binding_type == ServiceBinding.PERSIST_PURGE  :
               rdf_delete( next_binding, model, obj , mode)
            else:
                raise Exception( "service type not supported when post processing inferences")
            inference_chain_results.append(str( next_binding) )
            next_binding = next_binding.next_service

    return inference_chain_results

   
def build_rdf( gr,obj, oml, includemembers ) :  

    # would be nice to add some comments : as metadata on the graph? '# Turtle generated by django-rdf-io configurable serializer\n'  
    mappingsused = 0
    for om in oml :
        # check filter
        objfilter = getattr(om,'filter') 
        if objfilter and not apply_pathfilter(obj, objfilter ) :
            continue
        mappingsused += 1  
        try:
            tgt_id = getattr_path(obj,om.id_attr)[0]
        except (IndexError,ValueError) as e:
            raise ValueError("target id attribute {} not found".format( (om.id_attr ,)))
        if om.target_uri_expr[0] == '"' :   
            uribase = om.target_uri_expr[1:-1]
        else:
            uribase = getattr_path(obj,om.target_uri_expr)[0]
            
        tgt_id = str(tgt_id).replace(uribase,"")
        # strip uri base if present in tgt_id
        uribase = expand_curie(uribase)
        
 
        if not tgt_id:
            uri = uribase
        elif uribase[-1] == '/' or uribase[-1] == '#' :
            uri = "".join((uribase,tgt_id))
        else :
            uri = "/".join((uribase,tgt_id))
        
        subject = URIRef(uri)
        
        for omt in om.obj_type.all() :
            gr.add( (subject, RDF.type , as_resource(gr,omt.uri)) )
  
        # now get all the attribute mappings and add these in
        for am in AttributeMapping.objects.filter(scope=om) :
            if am.predicate[0] != ':' :
                _add_vals(gr, obj, subject, am.predicate, am.attr , am.is_resource)
            else:
                for predicate,valuelist in getattr_tuple_path(obj,(am.predicate[1:],am.attr)):
                    for value in valuelist:
                        is_resource = value[0] == '<' and value[-1:] == '>'
                        if is_resource :
                            # brute force quote - ignoring any string @lang or ^^ type stuff quote() handles
                            value = value[1:-1].join(('"','"'))
                        else :
                            value = quote(value) 
                        _add_vals(gr, obj, subject, str(predicate), value, is_resource)
        
        if includemembers:
            for cm in ChainedMapping.objects.filter(scope=om) :
                for val in getattr_path(obj,cm.attr):
                    try:
                        build_rdf( gr,val, (cm.chainedMapping,), includemembers )
                    except:
                        print( "Error serialising object %s as %s " % ( val, cm.attr ))
        
        for em in EmbeddedMapping.objects.filter(scope=om) :
            try:
                # three options - scalar value in which case attributes relative to basic obj, a mulitvalue obj or we have to look for related objects
                try:
                    valuelist = getattr_path(obj,em.attr)
                except:
                    valuelist = [obj,] 

                for value in valuelist :
                    newnode = None
 
                    for element in em.struct.split(";") :
                        try:
                            (predicate,expr) = element.split()
                        except:
                            predicate = None
                            expr = element
                            
                        # resolve any internal template parameters {x}
                        expr = expr.replace("{$URI}", uri )

                        is_resource = False
                        if expr.startswith("<") :
                            is_resource = True
                            expr = expr[1:-1].join(('"','"'))
                        elif expr.startswith("/") :
                            #value relativeto root obj  - retrieve and use as literal
                            try:
                                expr = iter(getattr_path(obj,expr[1:])).next()
                                if type(expr) == str :
                                    expr = expr.join( ('"','"'))
                            except:
                                raise ValueError( "Could not access value of %s from mapped object %s (/ is relative to the object being mapped" % (expr,obj) )
                        else:
                            is_resource = False
                        
                        for (lit,var,x,y) in Formatter().parse(expr) :
                            if var :
                                try:
                                    if var.startswith("^"):
                                        val = iter(getattr_path(obj,var[1:])).next()
                                    else:
                                        val = iter(getattr_path(value,var)).next()
                                    
                                    if is_resource:
                                        try:
                                            val = u.urlencode({ 'v' : val.encode('utf-8')})[2:]
                                        except:
                                            #not a string, just pass
                                            pass
                                    val = str(val)
                                except:
                                    val="{!variable not found : %s}" % var
                                expr = expr.replace(var.join(("{","}")), val )
                        if predicate :
                            # an internal struct has been found so add a new node if not ye done
                            if not newnode:
                                newnode = BNode()
                                gr.add( (subject, as_resource(gr,em.predicate) , newnode) )
                            _add_vals(gr, value, newnode, predicate, expr , is_resource)
                        else:
                            # add to parent
                            _add_vals(gr, value, subject, em.predicate, expr , is_resource)
            except Exception as e:
                import traceback; import sys; traceback.print_exc()
                print "Could not evaluate extended mapping %s : %s " % (e,em.attr), sys.exc_info()
                raise ValueError("Could not evaluate extended mapping %s : %s " % (e,em.attr))
    # do this after looping through all object mappings!
    return gr if mappingsused > 0 else None
                            
def _add_vals(gr, obj, subject, predicate, attr, is_resource ) :       
            if type(attr) == float or attr[0] in '\'\"' : # then a literal
                gr.add( (subject, as_resource(gr,predicate) , makenode(gr,attr,is_resource) ) )
            else :
                values = getattr_path(obj,attr)
                for value in values :
                    if not value :
                        continue
                    gr.add( (subject, as_resource(gr,predicate) , makenode(gr,value,is_resource) ) )
 
    
    
    
    
    