from rdf_io.signals.utils import *
# originally configured signals automatically - but because this results in circular dependencies with modules that set up object mappings this is deprecated
#signals.post_save.connect(setup_signals, sender=ObjectMapping)
#sync_signals()
