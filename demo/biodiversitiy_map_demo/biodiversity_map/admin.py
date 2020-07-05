# -*- coding: utf-8 -*-
# python manage.py admin_generator biodiversity_map >> biodiversity_map/admin.py
from django.contrib import admin

from .models import GeoLocation, HabitatClass, Habitat, Domain, Kingdom, Family, Genus, Organism

@admin.register(GeoLocation)
class GeoLocationAdmin(admin.ModelAdmin):
    list_display = (
        'geoinfo_id',
        'name',
        'coordinates_DD_lat',
        'coordinates_DD_long',
        'coordinates_DMS',
        'coordinates_DMM',
        'elevation',
        'openstreetmap',
        'googlemap',
    )
    search_fields = ('name',)


@admin.register(HabitatClass)
class HabitatClassAdmin(admin.ModelAdmin):
    list_display = ('class_id', 'habitat_class', 'description')


@admin.register(Habitat)
class HabitatAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ('habitat_id', 'name', 'description')
    raw_id_fields = ('habitat_classes',)
    search_fields = ('name',)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain_id', 'name', 'description')
    search_fields = ('name',)


@admin.register(Kingdom)
class KingdomAdmin(admin.ModelAdmin):
    list_display = ('kingdom_id', 'name', 'domain', 'description')
    list_filter = ('domain',)
    search_fields = ('name',)


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = (
        'family_id',
        'name',
        'common_name',
        'characteristics',
        'kingdom',
        'description',
    )
    list_filter = ('kingdom',)
    search_fields = ('name',)


@admin.register(Genus)
class GenusAdmin(admin.ModelAdmin):
    list_display = (
        'genus_id',
        'name',
        'common_name',
        'characteristics',
        'kingdom',
        'description',
    )
    list_filter = ('kingdom',)
    search_fields = ('name',)


@admin.register(Organism)
class OrganismAdmin(admin.ModelAdmin):
    list_display = (
        'organism_id',
        'species',
        'genus',
        'family',
        'kingdom',
        'domain',
        'description',
    )
    list_filter = ('genus', 'family', 'kingdom', 'domain')
    raw_id_fields = ('habitat', 'geolocation')
