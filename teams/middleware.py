from .models import Team
from hunts.models import Hunt

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
