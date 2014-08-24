from django.shortcuts import render_to_response, get_object_or_404

from thezombies.models import Agency

def home(request):
    agencies = Agency.objects.all()
    return render_to_response('home.html', {'agencies':agencies})

def agency(request, slug):
    agency = get_object_or_404(Agency, slug__exact=slug)
    return render_to_response('agency.html', {'agency':agency})
