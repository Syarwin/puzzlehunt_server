from datetime import datetime
from dateutil import tz
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib import messages
from django.db.models import F, Max, Count, Min, Subquery, OuterRef, Value
from django.db.models.fields import PositiveIntegerField
from django.db.models.functions import Lower
from huey.contrib.djhuey import result
from django.contrib.auth.decorators import login_required
import json
from copy import deepcopy
# from silk.profiling.profiler import silk_profile

from hunts.models import Guess, Hunt, Prepuzzle
from teams.models import Team, TeamPuzzleLink, PuzzleSolve, Person
from teams.forms import GuessForm, UnlockForm, EmailForm, LookupForm

DT_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def add_apps_to_context(context, request):
    context['available_apps'] = admin.site.get_app_list(request)
    return context

def get_last_hunt_or_none():
    last_hunts = Hunt.objects.filter(end_date__lt=timezone.now()).order_by('-end_date')
    if last_hunts.count() == 0:
      return None
    nb_puzzle = len([0 for episode in last_hunts.first().episode_set.all() for puzzle in episode.puzzle_set.all()])
    
    curr_hunt = last_hunts[:1].annotate(puz=Value(nb_puzzle, output_field=PositiveIntegerField())).first()  
    return curr_hunt
    
    

@login_required
def stats(request):
    ''' General stats of the hunt: #teams, #guesses, #puzzles solved, total time spent on the hunt... '''
    curr_hunt = get_last_hunt_or_none()
    if curr_hunt == None:
      context = {'hunt': None}
      return render(request, 'stats/stats.html', context)
    
    context = {'hunt': curr_hunt}
    return render(request, 'stats/stats.html', context)
    
    
    
@login_required
def teams(request):
    ''' General view of all teams:  rank, number of solved puzzles, finish time (if finished) '''
    curr_hunt = get_last_hunt_or_none()
    if curr_hunt == None:
      context = {'hunt': None}
      return render(request, 'stats/teams.html', context)
      
    teams = curr_hunt.team_set.all()
    all_teams = teams.annotate(solves=Count('solved'))
    all_teams = all_teams.annotate(last_time=Max('puzzlesolve__guess__guess_time'))
    all_teams = all_teams.order_by(F('solves').desc(nulls_last=True),
                                   F('last_time').asc(nulls_last=True))

    context = {'team_data': all_teams, 'hunt': curr_hunt}
    return render(request, 'stats/teams.html', context)


@login_required
def team(request):
    ''' Summary of a single team performance, asked by /?team=ID: time / duration per puzzle, rank on each, number of guesses, number of hints needed, #teammates with guesses '''
    curr_hunt = get_last_hunt_or_none()
    if curr_hunt == None:
      context = {'hunt': None}
      return render(request, 'stats/team.html', context)
      
      
    
    teams = curr_hunt.team_set.all()
    all_teams = teams.annotate(solves=Count('solved'))
    all_teams = all_teams.annotate(last_time=Max('puzzlesolve__guess__guess_time'))
    all_teams = all_teams.order_by(F('solves').desc(nulls_last=True),
                                   F('last_time').asc(nulls_last=True))

    team = Hunt.objects.get(is_current_hunt=True).team_from_user(request.user)
    if(team is None):
      solves_data = []
    else:
      solves = team.puzzlesolve_set.annotate(time=F('guess__guess_time'), puzId = F('puzzle__puzzle_id')).order_by('time')
      unlocks = team.teampuzzlelink_set.annotate(puzId = F('puzzle__puzzle_id'), name = F('puzzle__puzzle_name')).order_by('time')

      solves_data = []
      for unlock in unlocks.all():
        try:
          solve = solves.get(puzId=unlock.puzId)
          solves_data.append({'name' : unlock.name, 'sol_time': solve.time, 'duration':  str(timedelta(seconds=int((solve.time-unlock.time).total_seconds())))})
        except ObjectDoesNotExist:
          solves_data.append({'name' : unlock.name, 'sol_time': '' , 'duration':  str(timedelta(seconds=int((timezone.now()-unlock.time).total_seconds())))})

    context = {'solve_data': solves_data, 'hunt': curr_hunt, 'team': team}
    
    
    return render(request, 'stats/team.html', context)
    

@login_required
def puzzles(request):
    ''' Summary of all puzzles: #teams successful, fastest time / duration / smallest number of hints, average time / duration / number of hints, link to solution file '''
    curr_hunt = get_last_hunt_or_none()
    if curr_hunt == None:
      context = {'hunt': None}
      return render(request, 'stats/puzzles.html', context)
      
    context = {'hunt': curr_hunt}
    return render(request, 'stats/puzzles.html', context)
    
    

@login_required
def puzzle(request):
    ''' Summary of 1 puzzle results: each team duration, time solved, wrong guesses, number of hints seen, duration to get each eureka. Also show all eurekas / hints '''
    curr_hunt = get_last_hunt_or_none()
    if curr_hunt == None:
      context = {'hunt': None}
      return render(request, 'stats/puzzle.html', context)
      
    context = {'hunt': curr_hunt}
    return render(request, 'stats/puzzle.html', context)
    
    
@login_required
def charts(request):
    ''' CHARTSSSS: progress of all teams with toggles / top teams, spam contest by user / team , top teams time for each puzzle '''
    curr_hunt = get_last_hunt_or_none()
    if curr_hunt == None:
      context = {'hunt': None}
      return render(request, 'stats/charts.html', context)
      
    context = {'hunt': curr_hunt}
    return render(request, 'stats/charts.html', context)
    
    

