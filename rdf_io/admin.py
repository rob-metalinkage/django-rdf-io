from .models import *
from django.contrib import admin
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from .views import *
from django import forms
#from django.contrib.admin.widgets import SelectWidget
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse

class GenericMetaPropInline(admin.TabularInline):
    model = GenericMetaProp
    # readonly_fields = ('slug','created')
    #fields = ('code','namespace')
    # related_search_fields = {'label' : ('name','slug')}
    extra=1 
    

def publish_set_background(queryset,model,check,mode,logf):
    from django.core.files import File
    # import pdb; pdb.set_trace()
    import time
    
    with open(logf,'w') as f:
        proclog = File(f) 
        f.write("Publishing %s %ss in mode %s at %s<BR>" % ( str(len(queryset)), model, mode, time.asctime()))
        for msg in publish_set(queryset,model,check,mode):
            if( msg.startswith("Exception") ):
                em = "<strong>"
                emend = "</strong>"
            else:
                em = ""
                emend = ""
            f.write("".join(("<LI>",em,msg,emend,"</LI>")))
            f.flush()
        f.write ("<BR> publish action finished at %s<BR>" % (  time.asctime(),))
    
    
def publish_set_action(queryset,model,check=False,mode='PUBLISH'):
    import threading
    from django.conf import settings
    import os
    import time
    timestr = time.strftime("%Y%m%d-%H%M%S")
    logfname = '{}_batch_publish_{}.html'.format(model,timestr)
    try:
        logf = os.path.join(settings.BATCH_RDFPUB_LOG, logfname)
    except:
        logf = os.path.join(settings.STATIC_ROOT,logfname)
    t = threading.Thread(target=publish_set_background, args=(queryset,model,check,mode,logf), kwargs={})
    t.setDaemon(True)
    t.start()
    return "/static/" + logfname


 
def force_prefix_use(modeladmin, request, queryset):
    """ update selected Metaprops to use CURIE form with registered prefix """
    for obj in queryset.all() :
        obj.save()
force_prefix_use.short_description = "update selected Metaprops to use CURIE form with registered prefix"       
 
class GenericMetaPropAdmin(admin.ModelAdmin):
    search_fields = ['propname' ]
    actions= [force_prefix_use]
    pass

class ObjectTypeAdmin(admin.ModelAdmin):
    pass

class AttributeMappingInline(admin.TabularInline):
    model = AttributeMapping
    # readonly_fields = ('slug','created')
    #fields = ('code','namespace')
    # related_search_fields = {'label' : ('name','slug')}
    extra=1 

class EmbeddedMappingInline(admin.TabularInline):
    model = EmbeddedMapping
    # readonly_fields = ('slug','created')
    #fields = ('code','namespace')
    # related_search_fields = {'label' : ('name','slug')}
    extra=1 
 
class ChainedMappingInline(admin.TabularInline):
    model = ChainedMapping
    fk_name='scope'
    # readonly_fields = ('slug','created')
    fields = ('attr','predicate','chainedMapping')
    # related_search_fields = {'label' : ('name','slug')}
    extra=1 
    
class ObjectMappingAdmin(admin.ModelAdmin):
    search_fields = ['content_type__name' ]
    inlines = [   AttributeMappingInline, ChainedMappingInline, EmbeddedMappingInline]
    filter_horizontal = ('obj_type',)
    pass
    
class AttributeMappingAdmin(admin.ModelAdmin):
    pass

        
class EmbeddedMappingAdmin(admin.ModelAdmin):
    pass


class NamespaceAdmin(admin.ModelAdmin):
    list_display = ('uri','prefix','notes')
    fields = ('uri','prefix','notes')
    search_fields = ['uri','prefix' ]
#    related_search_fields = {'concept' : ('pref_label','definition')}
    #list_editable = ('name','slug')
    search_fields = ['uri','prefix']    

    
class ConfigVarAdmin(admin.ModelAdmin):
    pass

class ResourceMetaInline(admin.TabularInline):
    model = ResourceMeta
    verbose_name = 'Additional property'
    verbose_name_plural = 'Additional properties'
#    list_fields = ('pref_label', )
    show_change_link = True
    max_num = 20
    fields = ('subject','metaprop','value')
 #   list_display = ('pref_label',)
    extra = 1
   
IR = ContentType.objects.get_for_model(ImportedResource)
   
class ImportedResourceAdmin(admin.ModelAdmin):
    list_display = ('description', 'subtype', '__str__')
    search_fields = ['description','file','remote']  
    inlines = [ ResourceMetaInline , ]    
    actions= ['publish_options', ]
    resourcetype = 'importedresource'
    def get_queryset(self, request):
        qs = super(ImportedResourceAdmin, self).get_queryset(request)
        # import pdb; pdb.set_trace()
        return qs.filter(Q(subtype__isnull=True) | Q(subtype=IR ))      

    def publish_options(self,request,queryset):
        """Batch publish with a set of mode options"""
        if 'apply' in request.POST:
            # The user clicked submit on the intermediate form.
            # Perform our update action:
            if request.POST.get('mode') == "CANCEL" :
                self.message_user(request,
                              "Cancelled publish action")
            else:
                checkuri = 'checkuri' in request.POST
                logfile= publish_set_action(queryset,self.resourcetype,check=checkuri,mode=request.POST.get('mode'))
                self.message_user(request,
                              mark_safe('started publishing in {} mode for {} {}s at <A HREF="{}" target="_log">{}</A>'.format(request.POST.get('mode'),queryset.count(),self.resourcetype, logfile,logfile) ) )
            return HttpResponseRedirect(request.get_full_path())
        return render(request,
                      'admin/admin_publish.html',
                      context={'schemes':queryset, 
                        'pubvars': ConfigVar.getvars('PUBLISH') ,
                        'reviewvars': ConfigVar.getvars('REVIEW') ,
                        })

    
class ObjectBoundListFilter(admin.SimpleListFilter):
    title='Chain Start by Object Type'
    parameter_name = 'objtype'
    
    def lookups(self, request, model_admin):
        chains = ServiceBinding.objects.filter(object_mapping__content_type__isnull=False)        
        return set([(c.object_mapping.first().content_type.model, c.object_mapping.first().content_type.model) for c in chains])
        
    def queryset(self, request, qs):
        try:
            #import pdb; pdb.set_trace()
            if request.GET.get('objtype') :
                qs= qs.filter(object_mapping__content_type__model = request.GET.get('objtype'))
        except:
            pass
        return qs

class ChainListFilter(admin.SimpleListFilter):
    title='Chain members'
    parameter_name = 'chain_id'
    
    def lookups(self, request, model_admin):
        chains = ServiceBinding.objects.filter(object_mapping__name__isnull=False)        
        return [(c.id, c.object_mapping.first().name) for c in chains]
        
    def queryset(self, request, qs):
        try:
            pass
            #qs= qs.filter(object_mapping__id = request.GET.get('chain_id'))
        except:
            pass
        return qs

class NextChainWidget( forms.Select):
    def render(self, name, value, attrs=None):
        self.choices = self.form_instance.fields['next_service'].choices
        s = super(forms.Select, self).render(name, value, attrs)
        h="<BR/>"
        ind= "-> {}<BR/>"
        
        for next in  self.form_instance.instance.next_chain():
            h = h+ ind.format( str(next))
            ind = "--" + ind
  
        
        return mark_safe(s+ h )
        
class ServiceBindingAdminForm (forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ServiceBindingAdminForm, self).__init__(*args, **kwargs)
        self.fields['next_service'].widget = NextChainWidget()
        self.fields['next_service'].widget.form_instance = self
        
class ServiceBindingAdmin(admin.ModelAdmin) :
    list_display = ('title', 'binding_type', 'object_mapping_list')
    list_filter=(ObjectBoundListFilter,ChainListFilter,'binding_type')
    search_fields = ['title','binding_type'] 
    form = ServiceBindingAdminForm
    pass
    
admin.site.register(Namespace, NamespaceAdmin)  
admin.site.register(GenericMetaProp,GenericMetaPropAdmin)
admin.site.register(ObjectType, ObjectTypeAdmin)
admin.site.register(ObjectMapping, ObjectMappingAdmin)
#admin.site.register(AttributeMapping, AttributeMappingAdmin)
#admin.site.register(EmbeddedMapping, EmbeddedMappingAdmin)
admin.site.register(ImportedResource, ImportedResourceAdmin)

admin.site.register(ServiceBinding, ServiceBindingAdmin)
admin.site.register(ConfigVar, ConfigVarAdmin)