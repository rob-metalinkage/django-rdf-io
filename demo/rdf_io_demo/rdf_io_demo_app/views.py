from django.shortcuts import render



# Create your views here.

from django.http import HttpResponse
#from .models import SKOS_Biodiversity

def index(request):
    return HttpResponse("Hello, world. You're at the biodiv index.")