from django.db import models

class SKOS_Biodiversity:
    @staticmethod
    def init_SKOS_models_db():
        """[summary]

        :return: [description]
        :rtype: [type]
        """
        # biodiversity namespaces
        Namespace.objects.get_or_create( uri='http://some_rdf_site.org/biomodels/', defaults = { 'prefix' : 'bio' , 'notes': 'Data model for biodiversity' } )
        Namespace.objects.get_or_create( uri='http://some_rdf_site.org/data/geolocation/', defaults = { 'prefix' : 'geoloc' , 'notes': 'Geolocation data' } )
        Namespace.objects.get_or_create( uri='http://some_rdf_site.org/data/habitats/', defaults = { 'prefix' : 'hab' , 'notes': 'Habitat data' } )

        GeoLocation.add_SKOS_mapping_db()
        Habitat.add_SKOS_mapping_db()
        Domain.add_SKOS_mapping_db()
        Kingdom.add_SKOS_mapping_db()
        Family.add_SKOS_mapping_db()
        Genus.add_SKOS_mapping_db()
        Organism.add_SKOS_mapping_db()


class GeoLocation(models.Model):
    """ generic geo location information class to store location data, like DD: 54.0915461, 13.4028547 """
    geoinfo_id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, help_text="Unique location name")
    coordinates_DD_lat = models.DecimalField(max_digits=20, decimal_places=9, default=54.0915068, 
                         help_text="in Decimal degrees (DD) - latitude, e.g., 41.40338")
    coordinates_DD_long = models.DecimalField(max_digits=20, decimal_places=9, default=13.4029247, 
                                              help_text="in Decimal degrees (DD) - longitude, e.g., 2.17403 ")
    coordinates_DMS =  models.TextField(blank=True, default="""54deg5'29.434"N 13deg24'10.527"E""", help_text="""in Degrees, minutes, and seconds (DMS): 41deg24'12.2"N 2deg10'26.5"E""") # might need a syntax checker
    coordinates_DMM =  models.TextField(blank=True, default="41 24.2028, 2 10.4418", help_text="in Degrees and decimal minutes (DMM): 41 24.2028, 2 10.4418")
    elevation = models.IntegerField(default=0, help_text="elevation in m above sea level")
    openstreetmap = models.URLField(blank=True, help_text="OpenStreetMap (www.openstreetmap.org) link to address") # this could be autogenerated upon saved...
    googlemap = models.URLField(blank=True, help_text="google maps link to address") # this could be autogenerated upon saved...
    
    def __str__(self):
        return self.name or "" # self.openstreetmap
  
    @staticmethod
    def add_SKOS_mapping_db():
        (object_type,created) = ObjectType.objects.get_or_create(uri="geloc:Geolocation", defaults = { "label" : "Geolocation class" })

        # !! right now use quoted syntax, like "'hab:'" - this should be fixed in future releases
        sm = ObjectMapping.new_mapping(object_type, "biodiversity_map:Geolocatino", "Geolocation in RDF", "geolocation_id", "'geoloc:'" , auto_push=False)
        # specific mapping
        am = AttributeMapping(scope=sm, attr="name", predicate="rdfs:label", is_resource=False).save()
    
class HabitatClass(models.Model):
    """ classes of habitates, like maritim, terrestric, shore, ..  """
    class_id = models.AutoField(primary_key=True)
    habitat_class = models.TextField(unique=True, help_text="maritim, terrestric, shore")
    description = models.TextField(blank=True, help_text="description of the substance class")

    def __str__(self):
        return self.habitat_class or ''
        
    def __repr__(self):
        return self.habitat_class or u''
        
    class Meta:
        verbose_name_plural = 'HabitatClasses'

class Habitat(models.Model):
    """ """
    habitat_id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True, help_text="habitat name with namespaces, like sea.shore, sea.deepsee, land.vulcan")
    habitat_classes = models.ManyToManyField(HabitatClass,  blank=True, related_name="extra_data_addresses",
                              help_text="class of habitat, e.g. maritim, terrestric, shore, .. ")
    description = models.TextField(blank=True, help_text="description of the habitat")
    
    def __str__(self):
        return self.name or ''
        
    def __repr__(self):
        return self.contrib_caption or u''

    @staticmethod
    def add_SKOS_mapping_db():
        Namespace.objects.get_or_create( uri='http://some_rdf_site.org/data/habitats/', defaults = { 'prefix' : 'hab' , 'notes': 'Habitat data' } )

        (object_type,created) = ObjectType.objects.get_or_create(uri="bio:Habitat", defaults = { "label" : "Habitat class" })

        # !! right now use quoted syntax, like "'hab:'" - this should be fixed in future releases
        sm = ObjectMapping.new_mapping(object_type, "biodiversity_map:Habitat", "Habitats in RDF", "habitat_id", "'hab:'" , auto_push=False)
        # specific mapping
        am = AttributeMapping(scope=sm, attr="name", predicate="rdfs:label", is_resource=False).save()

class Domain(models.Model):
    """ taxonomic domain / superkingdom / empire: Archaea, Bacteria, and Eukarya """
    domain_id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True, help_text="domain name: Archaea, Bacteria, and Eukarya")
    description = models.TextField(blank=True, help_text="description of domain")

    def __str__(self):
        return self.name or ''
        
    def __repr__(self):
        return self.name or u''
        
    #~ class Meta:
        #~ verbose_name_plural = ''

    @staticmethod
    def add_SKOS_mapping_db():
        # add mapping here ...
        pass


class Kingdom(models.Model):
    """ taxonomic Kingdom / regnum : Animalia, Plantae, Fungi, Protista, 
        Archaea/Archaebacteria, and Bacteria/Eubacteria 
        might be deprecated 
    """
    kingdom_id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True, help_text="phylum name, like ")
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, blank=True, null=True, help_text="parent domain")
    description = models.TextField(blank=True, help_text="description of phylum")

    def __str__(self):
        return self.name or ''
        
    def __repr__(self):
        return self.name or u''

    @staticmethod
    def add_SKOS_mapping_db():
        # add mapping here ...
        pass

class Family(models.Model):
    """ taxonomic Family """
    family_id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True, help_text="phylum name, like ")
    common_name = models.TextField(blank=True, null=True, help_text="common phylum name, like ")
    characteristics = models.TextField(blank=True, null=True, help_text="characteristics of phylum")
    kingdom = models.ForeignKey(Domain, on_delete=models.CASCADE, blank=True, null=True, help_text="parent domain")
    description = models.TextField(blank=True, help_text="description of phylum / meaning of the word")

    def __str__(self):
        return self.name or ''
        
    def __repr__(self):
        return self.name or u''
        
    class Meta:
        verbose_name_plural = 'Families'

    @staticmethod
    def add_SKOS_mapping_db():
        # add mapping here ...
        pass

class Genus(models.Model):
    """ taxonomic Genus """
    genus_id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True, help_text="genus name, like ")
    common_name = models.TextField(blank=True, null=True, help_text="common phylum name, like ")
    characteristics = models.TextField(blank=True, null=True, help_text="characteristics of phylum")
    kingdom = models.ForeignKey(Domain, on_delete=models.CASCADE, blank=True, null=True, help_text="parent domain")
    description = models.TextField(blank=True, help_text="description of phylum / meaning of the word")

    def __str__(self):
        return self.name or ''
        
    def __repr__(self):
        return self.name or u''
        
    class Meta:
        verbose_name_plural = 'Genera'
    
    @staticmethod
    def add_SKOS_mapping_db():
        # add mapping here ...
        pass

class Organism(models.Model):
    """ organism / species / strain  or cell line """
    organism_id = models.AutoField(primary_key=True)
    species = models.TextField(blank=True, null=True, help_text="Echerichia, ... ")
    genus = models.ForeignKey(Genus, on_delete=models.CASCADE, null=True, blank=True, help_text="genus")
    family = models.ForeignKey(Family, on_delete=models.CASCADE, null=True, blank=True, help_text="orgenism's family")
    kingdom = models.ForeignKey(Kingdom, on_delete=models.CASCADE, null=True, blank=True, help_text="orgenism's kingdom")
    domain =  models.ForeignKey(Domain, on_delete=models.CASCADE, null=True, blank=True, help_text="orgenism's domain")
    habitat = models.ManyToManyField(Habitat, blank=True, help_text="orgenism's habitats")
    geolocation = models.ManyToManyField(GeoLocation, blank=True, help_text="orgenism's geolocation")

    description = models.TextField(blank=True, help_text="description of the organism")

    def __str__(self):
        return self.species or ''

    @staticmethod
    def add_SKOS_mapping_db():
        # add mapping here ...
        pass