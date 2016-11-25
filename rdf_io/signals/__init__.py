from rdf_io.signals.utils import *
 
signals.post_save.connect(setup_signals, sender=ObjectMapping)
sync_signals()
