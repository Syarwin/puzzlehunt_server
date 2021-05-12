from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, login, views
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, reverse
from django.db.models.functions import Lower
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import Http404, JsonResponse

import random
import re

from hunts.models import Hunt
from teams.models import Person, Team
from teams.forms import UserForm, PersonForm
from teams.utils import parse_attributes
from hunts.views.mixin import APITokenRequiredMixin

import logging
logger = logging.getLogger(__name__)




def account_login(request):
    """ A mostly static view to render the login selection. Next url parameter is preserved. """

    if 'next' in request.GET:
        context = {'next': request.GET['next']}
    else:
        context = {'next': "/"}

    return views.LoginView.as_view(template_name="auth/login.html")(request)


class SignUp(View):
    def get(self, request):
        """
        A view to create user and person objects from valid user POST data, as well as render
        the account creation form.
        """

        uf = UserForm(prefix='user')
        return render(request, "auth/signup.html", {'uf': uf})

    def post(self, request):
        uf = UserForm(request.POST, prefix='user')
        if uf.is_valid():
            user = uf.save()
            user.set_password(user.password)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            user.save()
            person = Person()
            person.user = user
            person.save()
            login(request, user)
            logger.info("User created: %s" % (str(person)))
            return redirect(reverse('current_hunt'))
        else:
            return render(request, "auth/signup.html", {'uf': uf})



def account_logout(request):
    """ A view to logout the user. """

    logout(request)
    messages.success(request, "Logout successful")
    if 'next' in request.GET:
        additional_url = request.GET['next']
    else:
        additional_url = ""
    return redirect(reverse('index'))



class Registration(LoginRequiredMixin, View):
    login_url = '/login/'

    """
    The view that handles team registration. Mostly deals with creating the team object from the
    post request. The rendered page is nearly entirely static.
    """
    def get(self, request):
        curr_hunt = Hunt.objects.get(is_current_hunt=True)
        team = curr_hunt.team_from_user(request.user)

        if(curr_hunt.is_locked):
            return redirect(reverse("index"))
        if(team is not None):
            return redirect(reverse('manage-team'))
        else:
            teams = curr_hunt.team_set.order_by(Lower('team_name'))
            return render(request, "auth/registration.html",
                          {'teams': teams, 'curr_hunt': curr_hunt})

    def post(self, request):
        curr_hunt = Hunt.objects.get(is_current_hunt=True)
        
        if(request.user.person.teams.filter(hunt=curr_hunt).count()>0):
            messages.error(request, "You already have a team for this hunt")
        elif(request.POST["form_type"] == "create_team"):
            if(curr_hunt.team_set.filter(team_name__iexact=request.POST.get("team_name")).exists()):
                messages.error(request, "The team name you have provided already exists.")
            elif(re.match(".*[A-Za-z0-9].*", request.POST.get("team_name"))):
                join_code = ''.join(random.choice("ACDEFGHJKMNPRSTUVWXYZ2345679") for _ in range(5))
                team = Team.objects.create(team_name=request.POST.get("team_name"), hunt=curr_hunt, join_code=join_code)
                request.user.person.teams.add(team)
                logger.info("User %s created team %s" % (str(request.user), str(team)))
                return redirect(reverse('manage-team'))
            else:
                messages.error(request, "Your team name must contain at least one alphanumeric character.")

        elif(request.POST["form_type"] == "join_team"):
            team = curr_hunt.team_set.get(team_name=request.POST.get("team_name"))
            if(len(team.person_set.all()) >= team.hunt.team_size):
                messages.error(request, "The team you have tried to join is already full.")
                team = None
            elif(team.join_code.lower() != request.POST.get("join_code").lower()):
                messages.error(request, "The team join code you have entered is incorrect.")
                team = None
            else:
                request.user.person.teams.add(team)
                logger.info("User %s joined team %s" % (str(request.user), str(team)))
                return redirect(reverse('manage-team'))

        teams = curr_hunt.team_set.order_by(Lower('team_name'))
        return render(request, "auth/registration.html",
                      {'teams': teams, 'curr_hunt': curr_hunt})


class ManageTeam(View):
    """
    The view that handles team registration. Mostly deals with creating the team object from the
    post request. The rendered page is nearly entirely static.
    """

    def get(self, request):
        curr_hunt = Hunt.objects.get(is_current_hunt=True)
        team = curr_hunt.team_from_user(request.user)

        if(team is not None):
            context = {'registered_team': team, 'curr_hunt': curr_hunt}
            context['token'] = team.token
            context['discord_url'] = curr_hunt.discord_url
            context['discord_bot_id'] = curr_hunt.discord_bot_id

            return render(request, "auth/manage-team.html",
                          context)
        else:
            return redirect(reverse('registration'))


    def post(self, request):
        curr_hunt = Hunt.objects.get(is_current_hunt=True)
        team = curr_hunt.team_from_user(request.user)

        if("form_type" in request.POST):
            if(request.POST["form_type"] == "leave_team"):
                request.user.person.teams.remove(team)
                logger.info("User %s left team %s" % (str(request.user), str(team)))
                if(team.person_set.count() == 0 and team.hunt.is_locked):
                    logger.info("Team %s was deleted because it was empty." % (str(team)))
                    team.delete()
                team = None
                messages.success(request, "You have successfully left the team.")
            elif(request.POST["form_type"] == "new_location" and team is not None):
                old_location = team.location
                team.location = request.POST.get("team_location")
                team.save()
                logger.info("User %s changed the location for team %s from %s to %s" %
                            (str(request.user), str(team.team_name), old_location, team.location))
                messages.success(request, "Location successfully updated")
            elif(request.POST["form_type"] == "new_name" and team is not None and
                    not team.hunt.in_reg_lockdown):
                if(curr_hunt.team_set.filter(team_name__iexact=request.POST.get("team_name")).exists()):
                    messages.error(request, "The team name you have provided already exists.")
                else:
                    old_name = team.team_name
                    team.team_name = request.POST.get("team_name")
                    team.save()
                    logger.info("User %s renamed team %s to %s" %
                                (str(request.user), old_name, team.team_name))
                    messages.success(request, "Team name successfully updated")

        return render(request, "auth/manage-team.html",
                      {'registered_team': team, 'curr_hunt': curr_hunt})



@login_required
def profile(request):
    """ A view to handle user information update POST data and render the user information form. """

    if request.method == 'POST':
        uf = UserForm(request.POST, instance=request.user)
        pf = PersonForm(request.POST, instance=request.user.person)
        if uf.is_valid() and pf.is_valid():
            user = uf.save()
            user.set_password(user.password)
            user.save()
            pf.save()
            login(request, user)
            messages.success(request, "User information successfully updated.")
        else:
            context = {'user_form': uf, 'person_form': pf}
            return render(request, "auth/user_profile.html", context)
    user_form = UserForm(instance=request.user)
    person_form = PersonForm(instance=request.user.person)
    context = {'user_form': user_form, 'person_form': person_form}
    return render(request, "auth/user_profile.html", context)
    

# interface for the discord bot
class TeamInfoView(APITokenRequiredMixin, View):
    def get(self, request, team_token):
        try:
            team = Team.objects.get(token=team_token)
        except Team.DoesNotExist:
            return JsonResponse({
                'result': 'Not Found',
                'message': 'Invalid team token',
            }, status=404)
        except Team.DoesNotExist:
            return JsonResponse({
                'result': 'Not Found',
                'message': 'Several teams share this token',
            }, status=404)
        return JsonResponse({
            'result': 'OK',
            'team': {
                'name': team.team_name,
                'nb_ep_solve': team.ep_solved.count()
            },
        })

    
