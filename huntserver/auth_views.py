from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, login, views
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from huntserver.utils import parse_attributes
from huntserver.info_views import index

from .models import Hunt
from .forms import UserForm, PersonForm

import logging
logger = logging.getLogger(__name__)


def login_selection(request):
    """ A mostly static view to render the login selection. Next url parameter is preserved. """

    if 'next' in request.GET:
        context = {'next': request.GET['next']}
    else:
        context = {'next': "/"}

    if(settings.USE_SHIBBOLETH):
        return render(request, "login_selection.html", context)
    else:
        return views.LoginView.as_view()(request)


def create_account(request):
    """
    A view to create user and person objects from valid user POST data, as well as render
    the account creation form.
    """

    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    teams = curr_hunt.real_teams.all().exclude(team_name="Admin").order_by('pk')
    if request.method == 'POST':
        uf = UserForm(request.POST, prefix='user')
        pf = PersonForm(request.POST, prefix='person')
        if uf.is_valid() and pf.is_valid():
            user = uf.save()
            user.set_password(user.password)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            user.save()
            person = pf.save(commit=False)
            person.user = user
            person.save()
            login(request, user)
            logger.info("User created: %s" % (str(person)))
            return index(request)
        else:
            return render(request, "create_account.html", {'uf': uf, 'pf': pf, 'teams': teams})
    else:
        uf = UserForm(prefix='user')
        pf = PersonForm(prefix='person')
        return render(request, "create_account.html", {'uf': uf, 'pf': pf, 'teams': teams})


def account_logout(request):
    """ A view to logout the user and *hopefully* also logout out the shibboleth system. """

    logout(request)
    messages.success(request, "Logout successful")
    if 'next' in request.GET:
        additional_url = request.GET['next']
    else:
        additional_url = ""
    if(settings.USE_SHIBBOLETH):
        next_url = "https://" + request.get_host() + additional_url
        return redirect("/Shibboleth.sso/Logout?return=" + next_url)
    else:
        return index(request)
