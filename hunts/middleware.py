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
from hunts.models import Hunt, Puzzle

class PuzzleMiddleware(object):
    """
    Automatically fetch the puzzle if kwargs[puzzle_id] is set
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.puzzle = None
        try:
            if 'puzzle_id' in view_kwargs:
                request.puzzle = Puzzle.objects.get(puzzle_id=view_kwargs['puzzle_id'])
        except Puzzle.DoesNotExist:
            request.puzzle = None


class HuntMiddleware(object):
    """
    Automatically fetch the hunt if the user is logged in
    Either use kwargs[hunt_num] or default to current hunt
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.hunt = None
        try:
            if 'hunt_num' in view_kwargs:
                request.hunt = Hunt.objects.get(hunt_number=view_kwargs['hunt_num'])
            else:
                if request.puzzle:
                    request.hunt = request.puzzle.episode.hunt
                else:
                    request.hunt = Hunt.objects.get(is_current_hunt=True)
        except Hunt.DoesNotExist:
            request.hunt = None
