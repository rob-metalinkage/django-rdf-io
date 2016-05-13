from django.db import models
from django.utils.translation import ugettext_lazy as _
# for django 1.7 +
#from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
import itertools

# helpers
def getattr_path(obj,path) :
    try :
        return _getattr_related(obj, path.replace('__','.').split('.'))
    except ValueError as e:
        raise ValueError("Failed to map '{}' on '{}' (cause {})".format(path, obj, e))
    
def _getattr_related(obj, fields):
    """
        get an attribute - if multi-valued will be a list object!
    """
    if not len(fields):
        return [obj,]
        
    field = fields.pop(0)
    # try to get - then check for django 1.7+ manager for related field
    try: 
        a = getattr(obj, field)
    except AttributeError:
        # then try to find objects of this type with a foreign key
        try:
            reltype = ContentType.objects.get(model=field)
        except ContentType.DoesNotExist as e :
            raise ValueError("Could not locate attribute or related model '{}' in element '{}'".format(field, type(obj)) )
        # id django 1.7+ we could just use field_set to get a manager :-(
        claz = reltype.model_class()
        for prop,val in claz.__dict__.items() :
            if type(val) is ReverseSingleRelatedObjectDescriptor and val.field.related.model == claz :
                a = claz.objects.filter(**{prop : obj})
                break
    
    try:
        return itertools.chain(*(_getattr_related(xx, fields) for xx in a.all()))
#        !list(itertools.chain(*([[1],[2]])))
    except:
        return _getattr_related(a, fields)

def validate_urisyntax(value):

    if value[0:4] == 'http' :
        URLValidator(verify_exists=False).__call__(value)
    else :
        parts = value.split(str=":")
        if len(parts) != 2 :
            raise ValidationError('invalid syntax')
        ns = Namespace.objects.get(prefix=part[0])
    
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
        return self.label 
 
class ObjectMapping(models.Model):
    """
        Maps an instance of a model to a resource (i.e. a URI with a type declaration) 
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    id_attr = models.CharField(_(u'ID Attribute'),help_text=_(u'for nested attribute use syntax a.b.c'),blank=False,max_length=250,editable=True)
    target_uri_expr = EXPR_Field(_(u'target namespace expression'), blank=False,editable=True)
    obj_type = models.ManyToManyField(ObjectType)
         
  
    def __unicode__(self):              # __unicode__ on Python 2
        return '.'.join( (self.content_type.app_label, self.content_type.model, self.id_attr )) + ' -> ' + '/'.join((self.target_uri_expr,'{' + self.id_attr + '}')) 
 

class AttributeMapping(models.Model):
    """
        records a mapping from an object mapping that defines the object to a value using a predicate
    """
    scope = models.ForeignKey(ObjectMapping)
    attr = EXPR_Field(_(u'source attribute'),blank=False,editable=True)
    predicate = CURIE_Field(_(u'predicate'),blank=False,editable=True)
    is_resource = models.BooleanField(_(u'as URI'))
    
    def __unicode__(self):
        return ( ' '.join((self.attr, self.predicate )))
