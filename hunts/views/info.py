from django.db.models.functions import Lower
from django.shortcuts import render
from django.contrib import messages

from hunts.models import Hunt
from teams.models import Team
from teams.forms import PersonForm, UserForm

import logging
logger = logging.getLogger(__name__)


def index(request):
    """ Main landing page view, mostly static with the exception of hunt info """
    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    team = curr_hunt.team_from_user(request.user)
    return render(request, "index.html", {'curr_hunt': curr_hunt, 'team': team})


def previous_hunts(request):
    """ A view to render the list of previous hunts, will show any hunt that is 'public' """
    old_hunts = []
    for hunt in Hunt.objects.all().order_by("hunt_number"):
        if(hunt.is_public):
            old_hunts.append(hunt)
    return render(request, "previous_hunts.html", {'hunts': old_hunts})
