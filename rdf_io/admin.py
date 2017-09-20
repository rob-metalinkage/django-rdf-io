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
    
class ObjectMappingAdmin(admin.ModelAdmin):
    search_fields = ['content_type__name' ]
    inlines = [   AttributeMappingInline, EmbeddedMappingInline]
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

class ImportedResourceAdmin(admin.ModelAdmin):
    pass

class ServiceBindingAdmin(admin.ModelAdmin) :
    list_display = ('title', 'binding_type')
    pass
    
admin.site.register(Namespace, NamespaceAdmin)  
admin.site.register(GenericMetaProp,GenericMetaPropAdmin)
admin.site.register(ObjectType, ObjectTypeAdmin)
admin.site.register(ObjectMapping, ObjectMappingAdmin)
admin.site.register(AttributeMapping, AttributeMappingAdmin)
admin.site.register(EmbeddedMapping, EmbeddedMappingAdmin)
admin.site.register(ImportedResource, ImportedResourceAdmin)

admin.site.register(ServiceBinding, ServiceBindingAdmin)