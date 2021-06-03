from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, reverse
from django.conf import settings
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseNotFound
from hunts.models import APIToken

class RequiredPuzzleAccessMixin():
    def dispatch(self, request, *args, **kwargs):
        if request.puzzle is None:
            return HttpResponseNotFound('<h1>Page not found</h1>')

        if not request.hunt.is_public:
            if(not request.user.is_authenticated):
                return redirect('%s?next=%s' % (reverse_lazy(settings.LOGIN_URL), request.path))

            elif (not request.user.is_staff):
                if request.team is None:
                    return redirect(reverse('registration'))
                elif request.puzzle.episode not in request.hunt.get_episodes(request.user,request.team) \
                        or request.puzzle not in request.team.puz_unlocked.all():
                    return redirect(reverse('hunt', kwargs={'hunt_num' : request.hunt.hunt_number }))
                    
        
        if request.hunt.is_finished and not request.user.is_authenticated:
                return redirect('%s?next=%s' % (reverse_lazy(settings.LOGIN_URL), request.path))

        return super().dispatch(request, *args, **kwargs)


class RequiredSolutionAccessMixin():
    def dispatch(self, request, *args, **kwargs):
        if request.puzzle is None:
            return HttpResponseNotFound('<h1>Page not found</h1>')

        if not request.user.is_authenticated:
                return redirect('%s?next=%s' % (reverse_lazy(settings.LOGIN_URL), request.path))

        if not request.user.is_staff and not request.hunt.is_finished:
            return HttpResponseNotFound('<h1>Page not found</h1>')
            
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
