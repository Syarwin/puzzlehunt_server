from .models import Team
from hunts.models import Hunt, Puzzle

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
                request.hunt = Hunt.objects.get(is_current_hunt=True)
        except Hunt.DoesNotExist:
            request.hunt = None


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
