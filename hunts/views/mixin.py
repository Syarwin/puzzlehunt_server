from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, reverse
from django.http import JsonResponse
from hunts.models import APIToken

class RequiredTeamMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff and request.team is None:
            if request.hunt is None:
                return redirect(reverse('index'))
            else:
                return redirect(reverse('registration'))
        else:
            return super().dispatch(request, *args, **kwargs)
            


class APITokenRequiredMixin():
    """
    API clients must pass their API token via the Authorization header using the format:
        Authorization: Bearer 12345678-1234-5678-1234-567812345678
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            authorization = request.headers['Authorization']
        except KeyError:
            return JsonResponse({
                'result': 'Unauthorized',
                'message': 'No Authorization header',
            }, status=401)
        try:
            (bearer, token) = authorization.split(' ')
        except ValueError:
            return JsonResponse({
                'result': 'Unauthorized',
                'message': 'Malformed Authorization header',
            }, status=401)
        if bearer != "Bearer":
            return JsonResponse({
                'result': 'Unauthorized',
                'message': 'Malformed Authorization header',
            }, status=401)
        try:
            APIToken.objects.get(token=token)
        except APIToken.DoesNotExist:
            return JsonResponse({
                'result': 'Unauthorized',
                'message': 'Invalid Bearer token',
            }, status=401)
        return super().dispatch(request, *args, **kwargs)

