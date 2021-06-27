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

from .models import Team
from hunts.models import Hunt

class TeamMiddleware(object):
    """
    Automatically fetch the team of hunt if the user is logged in
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.team = None

        if not request.user.is_authenticated or request.hunt is None:
            return

        request.team = request.hunt.team_from_user(request.user)
