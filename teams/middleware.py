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
