from .models import *
from django.contrib import admin

class GenericMetaPropInline(admin.TabularInline):
    model = GenericMetaProp
    # readonly_fields = ('slug','created')
    #fields = ('code','namespace')
    # related_search_fields = {'label' : ('name','slug')}
    extra=1 
    

class GenericMetaPropAdmin(admin.ModelAdmin):
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
#    related_search_fields = {'concept' : ('pref_label','definition')}
    #list_editable = ('name','slug')
    search_fields = ['uri','prefix']    

    
class ConfigVarAdmin(admin.ModelAdmin):
    pass
    
class ImportedResourceAdmin(admin.ModelAdmin):
#    list_display = ('file', 'remote', 'resource_type')
    search_fields = ['description','file','remote']    
    pass

    
class ObjectBoundListFilter(admin.SimpleListFilter):
    title='Chain Start by Object Type'
    parameter_name = 'objtype'
    
    def lookups(self, request, model_admin):
        chains = ServiceBinding.objects.filter(object_mapping__isnull=False)        
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
        chains = ServiceBinding.objects.filter(object_mapping__isnull=False)        
        return [(c.id, c.object_mapping.first().name) for c in chains]
        
    def queryset(self, request, qs):
        try:
            pass
            #qs= qs.filter(object_mapping__id = request.GET.get('chain_id'))
        except:
            pass
        return qs
        
class ServiceBindingAdmin(admin.ModelAdmin) :
    list_display = ('title', 'binding_type', 'next_service')
    list_filter=(ObjectBoundListFilter,ChainListFilter,'binding_type')
    search_fields = ['title','binding_type']    
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