# Copyright (C) 2018 The MindbreakersServer Contributors.
#
# This file is part of MindbreakersServer.
#
# MindbreakersServer is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# MindbreakersServer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Hunter2.  If not, see <http://www.gnu.org/licenses/>.

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
