from datetime import datetime
from dateutil import tz
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib import messages
from django.db.models import F, Max, Count, Min, Subquery, OuterRef
from django.db.models.fields import PositiveIntegerField
from django.db.models.functions import Lower
from huey.contrib.djhuey import result
import json
from copy import deepcopy
# from silk.profiling.profiler import silk_profile

from hunts.models import Guess, Hunt, Puzzle, Episode
from teams.models import Team, TeamPuzzleLink, PuzzleSolve, Person
from teams.forms import GuessForm, UnlockForm, EmailForm, LookupForm

DT_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


@staff_member_required
def index(request):
    context = {'hunt': Hunt.objects.get(is_current_hunt=True)}
    return render(request, 'staff/index.html', context)



@staff_member_required
def queue(request):
    """
    A view to handle queue response updates via POST, handle guess update requests via AJAX,
    and render the queue page. Guesss are pre-rendered for standard and AJAX requests.
    """

    if request.method == 'POST':
        form = GuessForm(request.POST)
        if not form.is_valid():
            return HttpResponse(status=400)
        response = form.cleaned_data['response']
        s = Guess.objects.get(pk=form.cleaned_data['sub_id'])
        s.update_response(response)
        guesss = [s]

    elif request.is_ajax():
        last_date = datetime.strptime(request.GET.get("last_date"), DT_FORMAT)
        last_date = last_date.replace(tzinfo=tz.gettz('UTC'))
        guesss = Guess.objects.filter(modified_date__gt=last_date)
        guesss = guesss.exclude(team__location="DUMMY")
        team_id = request.GET.get("team_id")
        puzzle_id = request.GET.get("puzzle_id")
        if(team_id and team_id != "None"):
            guesss = guesss.filter(team__pk=team_id)
        if(puzzle_id and puzzle_id != "None"):
            guesss = guesss.filter(puzzle__pk=puzzle_id)

    else:
        page_num = request.GET.get("page_num")
        team_id = request.GET.get("team_id")
        puzzle_id = request.GET.get("puzzle_id")
        hunt = Hunt.objects.get(is_current_hunt=True)
        guesss = Guess.objects.filter(puzzle__episode__hunt=hunt).exclude(team__location="DUMMY")
        arg_string = ""
        if(team_id):
            team_id = int(team_id)
            guesss = guesss.filter(team__pk=team_id)
            arg_string = arg_string + ("&team_id=%s" % team_id)
        if(puzzle_id):
            puzzle_id = int(puzzle_id)
            guesss = guesss.filter(puzzle__pk=puzzle_id)
            arg_string = arg_string + ("&puzzle_id=%s" % puzzle_id)
        guesss = guesss.select_related('team', 'puzzle').order_by('-pk')
        pages = Paginator(guesss, 30)
        try:
            guesss = pages.page(page_num)
        except PageNotAnInteger:
            guesss = pages.page(1)
        except EmptyPage:
            guesss = pages.page(pages.num_pages)
        puzzle_list = [puzzle for episode in hunt.episode_set.all() for puzzle in episode.puzzle_set.all()]

    form = GuessForm()
    try:
        last_date = Guess.objects.latest('modified_date').modified_date.strftime(DT_FORMAT)
    except Guess.DoesNotExist:
        last_date = timezone.now().strftime(DT_FORMAT)
    guess_list = [render_to_string('staff/queue_row.html', {'guess': guess},
                                        request=request)
                       for guess in guesss]
                       

    if request.is_ajax() or request.method == 'POST':
        context = {'guess_list': guess_list, 'last_date': last_date}
        return HttpResponse(json.dumps(context))
    else:
        context = {'form': form, 'page_info': guesss, 'arg_string': arg_string,
                   'guess_list': guess_list, 'last_date': last_date, 'hunt': hunt,
                   'puzzle_id': puzzle_id, 'team_id': team_id, 'puzzle_list': puzzle_list}
        return render(request, 'staff/queue.html', context)


@staff_member_required
def progress(request, ep_pk):
    """
    A view to handle puzzle unlocks via POST, handle unlock/solve update requests via AJAX,
    and render the progress page. Rendering the progress page is extremely data intensive and so
    the view involves a good amount of pre-fetching.
    """
    
    episode = get_object_or_404(Episode, pk=ep_pk)

    if request.method == 'POST':
        if "action" in request.POST:
            if request.POST.get("action") == "unlock":
                form = UnlockForm(request.POST)
                if form.is_valid():
                    t = Team.objects.get(pk=form.cleaned_data['team_id'])
                    p = Puzzle.objects.get(puzzle_id=form.cleaned_data['puzzle_id'])
                    if(p not in t.puz_unlocked.all()):
                        u = TeamPuzzleLink.objects.create(team=t, puzzle=p, time=timezone.now())
                        return HttpResponse(json.dumps(u.serialize_for_ajax()))
                    else:
                        return HttpResponse(status=200)
            if request.POST.get("action") == "unlock_all":
                p = Puzzle.objects.get(pk=request.POST.get('puzzle_id'))
                response = []
                for team in p.episode.hunt.team_set.all():
                    if(p not in team.puz_unlocked.all()):
                        u = TeamPuzzleLink.objects.create(team=team, puzzle=p, time=timezone.now())
                        response.append(u.serialize_for_ajax())
                return HttpResponse(json.dumps(response))
        return HttpResponse(status=400)

    elif request.is_ajax():
        update_info = []
        if not ("last_solve_pk" in request.GET and
                "last_unlock_pk" in request.GET and
                "last_guess_pk" in request.GET):
            return HttpResponse(status=404)
        results = []

        last_solve_pk = request.GET.get("last_solve_pk")
        solves = PuzzleSolve.objects.filter(pk__gt=last_solve_pk, episode=episode)
        for solve in solves:
            results.append(solve.serialize_for_ajax())

        last_unlock_pk = request.GET.get("last_unlock_pk")
        unlocks = TeamPuzzleLink.objects.filter(pk__gt=last_unlock_pk)
        for unlock in unlocks:
            results.append(unlock.serialize_for_ajax())

        last_guess_pk = request.GET.get("last_guess_pk")
        guesss = Guess.objects.filter(pk__gt=last_guess_pk)
        for guess in guesss:
            if(not guess.team.puz_solved.filter(pk=guess.puzzle.pk).exists()):
                results.append(guess.serialize_for_ajax())

        if(len(results) > 0):
            try:
                last_solve_pk = PuzzleSolve.objects.latest('id').id
            except PuzzleSolve.DoesNotExist:
                last_solve_pk = 0
            try:
                last_unlock_pk = TeamPuzzleLink.objects.latest('id').id
            except TeamPuzzleLink.DoesNotExist:
                last_unlock_pk = 0
            try:
                last_guess_pk = Guess.objects.latest('id').id
            except Guess.DoesNotExist:
                last_guess_pk = 0
            update_info = [last_solve_pk, last_unlock_pk, last_guess_pk]
        response = json.dumps({'messages': results, 'update_info': update_info})
        return HttpResponse(response)

    else:
        curr_hunt = Hunt.objects.get(is_current_hunt=True)
        teams = curr_hunt.team_set.all().order_by('team_name')
#        puzzles = curr_hunt.puzzle_set.all().order_by('puzzle_number')
        
        
        puzzles = [p for p in episode.puzzle_set.order_by('puzzle_number')]
#        puzzles = [p  for episode in curr_hunt.episode_set.order_by('ep_number').all() for p in episode.puzzle_set.order_by('puzzle_number')]
        # An array of solves, organized by team then by puzzle
        # This array is essentially the grid on the progress page
        # The structure is messy, it was built part by part as features were added

        sol_dict = {}
        puzzle_dict = {}
        for puzzle in puzzles:
            puzzle_dict[puzzle.pk] = ['locked', puzzle.puzzle_id]
        for team in teams:
            sol_dict[team.pk] = deepcopy(puzzle_dict)

        data = TeamPuzzleLink.objects.filter(puzzle__episode=episode)
        data = data.values_list('team', 'puzzle').annotate(Max('time'))

        for point in data:
            sol_dict[point[0]][point[1]] = ['unlocked', point[2]]

        data = Guess.objects.filter(puzzle__episode=episode)
        data = data.values_list('team', 'puzzle').annotate(Max('guess_time'))
        data = data.annotate(Count('puzzlesolve'))

        for point in data:
            if(point[3] == 0):
                sol_dict[point[0]][point[1]].append(point[2])
            else:
                sol_dict[point[0]][point[1]] = ['solved', point[2]]
        sol_list = []
        for team in teams:
            puzzle_list = [[puzzle.puzzle_id] + sol_dict[team.pk][puzzle.pk] for puzzle in puzzles]
            sol_list.append({'team': {'name': team.team_name, 'pk': team.pk},
                             'puzzles': puzzle_list})

        try:
            last_solve_pk = PuzzleSolve.objects.latest('id').id
        except PuzzleSolve.DoesNotExist:
            last_solve_pk = 0
        try:
            last_unlock_pk = TeamPuzzleLink.objects.latest('id').id
        except TeamPuzzleLink.DoesNotExist:
            last_unlock_pk = 0
        try:
            last_guess_pk = Guess.objects.latest('id').id
        except Guess.DoesNotExist:
            last_guess_pk = 0
        context = {'puzzle_list': puzzles, 'team_list': teams, 'sol_list': sol_list,
                   'last_unlock_pk': last_unlock_pk, 'last_solve_pk': last_solve_pk,
                   'last_guess_pk': last_guess_pk, 'hunt': curr_hunt}
        return render(request, 'staff/progress.html', context)




# background color of overview row
def getColor(minutes): 
    if minutes < 0:
      return "rgb(192,163,255)"
    if (minutes < 40):
      return "rgb(" + str(int(168*(1-minutes/40.)+255*minutes/40.))  + ",255,163)"
    elif (minutes < 80):
      minutes -= 40
      return "rgb(255," + str(int(255*(1-minutes/40.)+163*minutes/40.))  + ",163)"
    else:
      return "rgb(255,163,163)"

@staff_member_required
def overview(request):
    """
    A view to show the current state of each team on their last unlocked puzzle (if it is not solved)
    """
    # not relevant if puzzles unlocked before are unsolved

    # TODO no idea about the performance of this code, in terms of prefecthing database accesses
    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    teams = curr_hunt.team_set.all().order_by('team_name')

    sol_list = []
    for team in teams:
      puz_solved = team.puz_solved
      nb_solve = puz_solved.count()
      puzzle_unlock = team.teampuzzlelink_set.order_by('time').last()
      if (puzzle_unlock == None or (puzzle_unlock.puzzle in puz_solved.all())):
        sol_list.append({'team': team.team_name,
                       'puzzle': {'name': 'None found', 'time': '-', 'index': nb_solve, 'color': "rgb(163,163,163)"},
                       'guesses': {'nb' : '-' , 'last': '...', 'time': '-' },
                       'eurekas': {'nb' : 0 , 'last': '...', 'time': '-', 'total': 1},
                       'hints': {'nb' : 0 , 'last_time': '-', 'next_time': '-', 'total': 1},
                       'admin_eurekas' : []
                       })
        continue
      puzzle = puzzle_unlock.puzzle
      puzzle_name = puzzle.puzzle_name
      time_stuck = max(-1,int((timezone.now() - puzzle.starting_time_for_team(team)).total_seconds()/60))
      color = getColor(time_stuck)
      guesses = Guess.objects.filter(puzzle=puzzle, team=team).order_by('guess_time')
      nb_guess = guesses.count()
      lastguess = guesses.last()
      text_lastguess = '' if lastguess == None else lastguess.guess_text
      time_lastguess = 0 if lastguess == None else int((timezone.now() - lastguess.guess_time).total_seconds()/60)
      team_eurekas = team.eurekas.filter(puzzle=puzzle, admin_only=False).annotate(time=F('teameurekalink__time')).order_by('time')
      lasteureka = team_eurekas.last()
      time_lasteureka = 0 if lasteureka == None else int((timezone.now() - lasteureka.time).total_seconds()/60)
      text_lasteureka = '' if lasteureka== None else lasteureka.answer
      total_eureka = puzzle.eureka_set.filter(admin_only=False).count()

      admin_eurekas = team.eurekas.filter(puzzle=puzzle, admin_only=True).annotate(time=F('teameurekalink__time')).order_by('time')
      list_admin_eurekas = []
      for eureka in admin_eurekas.all():
        list_admin_eurekas.append({'txt': eureka.answer, 'time': int((timezone.now() - eureka.time).total_seconds()/60)})

      hints = puzzle.hint_set
      total_hints = hints.count()
      team_hints = 0
      last_hint_time = 360
      next_hint_time = 360 # default max time: 6h
      for hint in hints.all():
          delay = hint.delay_for_team(team) - (timezone.now() - hint.starting_time_for_team(team))
          delay = delay.total_seconds()
          if delay < 0:
            team_hints += 1
            last_hint_time = int(min(last_hint_time, -delay/60))
          else:
            next_hint_time = int(min(next_hint_time, delay/60))
      if last_hint_time == 360:
        last_hint_time = -1
      if next_hint_time == 360:
        next_hint_time = -1

      sol_list.append({'team': team.team_name,
                       'puzzle': {'name': puzzle_name, 'time': time_stuck, 'index': nb_solve+1, 'color': color},
                       'guesses': {'nb' : nb_guess , 'last': text_lastguess, 'time': time_lastguess },
                       'eurekas': {'nb' : team_eurekas.count() , 'last': text_lasteureka, 'time': time_lasteureka, 'total': total_eureka},
                       'hints': {'nb' : team_hints , 'last_time': last_hint_time, 'next_time': next_hint_time, 'total': total_hints},
                       'admin_eurekas' : list_admin_eurekas,
                       })

    context = {'data': sol_list, 'hunt':curr_hunt}
    return render(request, 'staff/overview.html', context)



@staff_member_required
#  most of this seemed useless / may be totally replaced by stats/ Redirect out of this for now
def charts(request):
    """ A view to render the charts page. Mostly just collecting and organizing data """


    return render(request, 'staff/charts.html', {})




@staff_member_required
def hunt_management(request):
    """ A view to render the hunt management page """

    hunts = Hunt.objects.all()

    puzzles = Puzzle.objects.all()

    context = {'hunts': hunts, 'puzzles': puzzles , 'hunt':curr_hunt}
    return render(request, 'staff/hunt_management.html', context)


@staff_member_required
def hunt_info(request):
    """ A view to render the hunt info page, which contains room and allergy information """

    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    if request.method == 'POST':
        if "json_data" in request.POST:
            team_data = json.loads(request.POST.get("json_data"))
            for pair in team_data:
                try:
                    team = Team.objects.get(id=pair['id'])
                    if(team.hunt == curr_hunt):
                        team.location = pair["location"]
                        team.save()
                except ObjectDoesNotExist:
                    return HttpResponse('bad data')
        return HttpResponse('teams updated!')
    else:
        teams = curr_hunt.team_set
        people = Person.objects.filter(teams__hunt=curr_hunt)
        try:
            old_hunt = Hunt.objects.get(hunt_number=curr_hunt.hunt_number - 1)
            new_people = people.filter(user__date_joined__gt=old_hunt.end_date)
        except Hunt.DoesNotExist:
            new_people = people

        need_teams = teams.filter(location="need_a_room") | teams.filter(location="needs_a_room")
        have_teams = (teams.exclude(location="need_a_room")
                           .exclude(location="needs_a_room")
                           .exclude(location="off_campus"))
        offsite_teams = teams.filter(location="off_campus")

        context = {'hunt': curr_hunt,
                   'people': people,
                   'new_people': new_people,
                   'need_teams': need_teams.order_by('id').all(),
                   'have_teams': have_teams.all(),
                   'offsite_teams': offsite_teams.all(),
                   }
        return render(request, 'staff/staff_hunt_info.html', context)


@staff_member_required
def control(request):
    """
    A view to handle all of the different management actions from staff users via POST requests.
    This view is not responsible for rendering any normal pages.
    """

    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    if(request.method == 'GET' and "action" in request.GET):
        if(request.GET['action'] == "check_task"):
            task_result = result(request.GET['task_id'])
            if(task_result is None):
                response = {"have_result": False, "result_text": ""}
            else:
                response = {"have_result": True, "result_text": task_result}
            return HttpResponse(json.dumps(response))

    if(request.method == 'POST' and "action" in request.POST):
        if(request.POST["action"] == "initial"):
            if(curr_hunt.is_open):
                teams = curr_hunt.team_set.all().order_by('team_name')
            else:
                teams = curr_hunt.team_set.filter(playtester=True).order_by('team_name')
            for team in teams:
                team.unlock_puzzles_and_episodes()
            messages.success(request, "Initial puzzles released")
            return redirect('hunt_management')
        if(request.POST["action"] == "reset"):
            teams = curr_hunt.team_set.all().order_by('team_name')
            for team in teams:
                team.reset()
            messages.success(request, "Progress reset")
            return redirect('hunt_management')

        if(request.POST["action"] == "new_current_hunt"):
            new_curr = Hunt.objects.get(hunt_number=int(request.POST.get('hunt_number')))
            new_curr.is_current_hunt = True
            new_curr.save()
            messages.success(request, "Set new current hunt")
            return redirect('hunt_management')

        else:
            return HttpResponseNotFound('access denied')



@staff_member_required
def lookup(request):
    """
    A view to search for users/teams
    """
    person = None
    team = None
    hunt = Hunt.objects.get(is_current_hunt=True)
    if request.method == 'POST':
        lookup_form = LookupForm(request.POST)
        if lookup_form.is_valid():
            search_string = lookup_form.cleaned_data['search_string']
            results = {'teams': Team.objects.search(search_string),
                       'people': Person.objects.search(search_string)}
    else:
        if("person_pk" in request.GET):
            person = Person.objects.get(pk=request.GET.get("person_pk"))
        if("team_pk" in request.GET):
            team = Team.objects.get(pk=request.GET.get("team_pk"))
            team.latest_guesss = team.guess_set.values_list('puzzle')
            team.latest_guesss = team.latest_guesss.annotate(Max('guess_time'))
            all_teams = team.hunt.team_set.annotate(solves=Count('puz_solved'))
            all_teams = all_teams.annotate(last_time=Max('puz_solved__guess__guess_time'))
            ids = all_teams.order_by(F('solves').desc(nulls_last=True),
                                     F('last_time').asc(nulls_last=True))
            team.rank = list(ids.values_list('pk', flat=True)).index(team.pk) + 1
            
        lookup_form = LookupForm()
        results = {}

    puzzle_list = [puzzle for episode in hunt.episode_set.all() for puzzle in episode.puzzle_set.all()]
    context = {'lookup_form': lookup_form, 'results': results, 'person': person, 'team': team,
               'hunt': hunt, 'puzzle_list': puzzle_list}
    return render(request, 'staff/lookup.html', context)


@staff_member_required
def puzzle_dag(request):
    """ A view to render the DAG of puzzles unlocking relations """

    puzzles = Puzzle.objects.all()
    episodes = Episode.objects.all()
    hunts = Hunt.objects.all()

    context = {'puzzles': puzzles, 'episodes':episodes, 'hunts': hunts, 'hunt': Hunt.objects.get(is_current_hunt=True)}
    return render(request, 'staff/puzzle_dag.html', context)
