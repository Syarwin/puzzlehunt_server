from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, reverse

class RequiredTeamMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.team is None:
            if request.hunt is None:
                return redirect(reverse('huntserver:index'))
            else:
                return redirect(reverse('huntserver:registration'))
        else:
            return super().dispatch(request, *args, **kwargs)
