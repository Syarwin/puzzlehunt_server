from django.db.models.functions import Lower
from django.shortcuts import render
from django.contrib import messages

from hunts.models import Hunt
from teams.models import Team
from teams.forms import PersonForm, UserForm


def index(request):
    """ Main landing page view, mostly static with the exception of hunt info """
    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    team = curr_hunt.team_from_user(request.user)
    return render(request, "index.html", {'curr_hunt': curr_hunt, 'team': team})
