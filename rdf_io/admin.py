from .models import *
from django.contrib import admin


class ObjectTypeAdmin(admin.ModelAdmin):
    pass

class AttributeMappingInline(admin.TabularInline):
    model = AttributeMapping
    # readonly_fields = ('slug','created')
    #fields = ('code','namespace')
    # related_search_fields = {'label' : ('name','slug')}
    extra=1 
    
class ObjectMappingAdmin(admin.ModelAdmin):
    search_fields = ['content_type__name' ]
    inlines = [   AttributeMappingInline,]
    pass
    
class AttributeMappingAdmin(admin.ModelAdmin):
    pass

    
class NamespaceAdmin(admin.ModelAdmin):
    list_display = ('uri','prefix','notes')
    fields = ('uri','prefix','notes')
#    related_search_fields = {'concept' : ('pref_label','definition')}
    #list_editable = ('name','slug')
    search_fields = ['uri','prefix']    

    
admin.site.register(Namespace, NamespaceAdmin)  
    
admin.site.register(ObjectType, ObjectTypeAdmin)
admin.site.register(ObjectMapping, ObjectMappingAdmin)
admin.site.register(AttributeMapping, AttributeMappingAdmin)