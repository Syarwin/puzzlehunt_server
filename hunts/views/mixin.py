from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, reverse

class RequiredTeamMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff and request.team is None:
            if request.hunt is None:
                return redirect(reverse('index'))
            else:
                return redirect(reverse('registration'))
        else:
            return super().dispatch(request, *args, **kwargs)
