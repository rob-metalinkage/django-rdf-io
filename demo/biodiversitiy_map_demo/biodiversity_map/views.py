from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse
from models import SKOS_Biodiversity

def index(request):
    return HttpResponse("Hello, world. You're at the biodiv index.")

def init_skos_models(request):
    """alternative route to init the SKOS models (in stead of management command)

    :param request: [description]
    :type request: [type]
    """    
    # check if db entries are present, otherwise create ....
    
    # SKOS_Biodiversity.init_SKOS_models_db()
    pass