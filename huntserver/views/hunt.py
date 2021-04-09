from datetime import datetime
from dateutil import tz
from django.conf import settings
from datetime import timedelta
from ratelimit.utils import is_ratelimited
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, RequestContext
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.utils.encoding import smart_str
from django.db.models import F
from django.urls import reverse_lazy, reverse
from pathlib import Path
import json
import os
import re

from huntserver.models import Puzzle, Hunt, Guess, Unlockable, Prepuzzle
from .mixin import RequiredTeamMixin

import logging
logger = logging.getLogger(__name__)

DT_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def protected_static(request, file_path):
    """
    A view to serve protected static content. Does a permission check and if it passes,
    the file is served via X-Sendfile.
    """

    allowed = False
    path = Path(file_path)
    base = path.parts[0]
    response = HttpResponse()
    if(len(path.parts) < 2):
        return HttpResponseNotFound('<h1>Page not found</h1>')

    if(base == "puzzles" or base == "solutions"):
        puzzle_id = re.match(r'[0-9a-fA-F]+', path.parts[1])
        if(puzzle_id is None):
            return HttpResponseNotFound('<h1>Page not found</h1>')

        puzzle = get_object_or_404(Puzzle, puzzle_id=puzzle_id.group(0))
        hunt = puzzle.episode.hunt
        user = request.user
        disposition = 'filename="{}_{}"'.format(puzzle.safename, path.name)
        response['Content-Disposition'] = disposition
        if (hunt.is_public or user.is_staff):
            allowed = True
        elif(base == "puzzles"):  # This is messy and the most common case, this should be fixed
            team = hunt.team_from_user(user)
            if (team is not None and puzzle in team.unlocked.all()):
                allowed = True
    else:
        allowed = True

    if allowed:
        pathname = smart_str(os.path.join(settings.MEDIA_ROOT, file_path))
        try:
           with open(pathname, "rb") as f:
              return HttpResponse(f.read(), content_type="image/png")
        except IOError:
           return HttpResponseNotFound('<h1>Page not found</h1>')
    else:
        logger.info("User %s tried to access %s and failed." % (str(request.user), file_path))

    return HttpResponseNotFound('<h1>Page not found</h1>')


def current_hunt(request):
    """ A simple view that calls ``huntserver.hunt_views.hunt`` with the current hunt's number. """
    return redirect(reverse('huntserver:hunt', kwargs={'hunt_num' : Hunt.objects.get(is_current_hunt=True).hunt_number}))


class HuntIndex(View):
    def get(self, request, hunt_num):
        """
        The main view to render hunt templates. Does various permission checks to determine the set
        of puzzles to display and then renders the string in the hunt's "template" field to HTML.
        """
        user = request.user
        hunt = request.hunt # Populated by middleware
        team = request.team # Populated by middleware

        # Admins get all access, wrong teams/early lookers get an error page
        # real teams get appropriate puzzles, and puzzles from past hunts are public
        if not hunt.can_access(user, team):
            if(hunt.is_locked):
                return redirect(reverse("huntserver:index"))
            if(hunt.is_open):
                return redirect(reverse('huntserver:registration'))

        episodes = sorted(hunt.get_episodes(user, team), key=lambda p: p.ep_number)
        puzzles = hunt.get_puzzle_list(user, team)
        context = {'hunt': hunt, 'episodes': episodes, 'team': team, 'puzzles':puzzles}
        return render(request, 'hunt/hunt_example.html', context)
        #return HttpResponse(Template(hunt.template).render(RequestContext(request, context)))


def prepuzzle(request, prepuzzle_num):
    """
    A view to handle answer guesss via POST and render the prepuzzle's template.
    """

    puzzle = Prepuzzle.objects.get(pk=prepuzzle_num)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            user_answer = re.sub(r"[ _\-;:+,.!?]", "", form.cleaned_data['answer'])

            # Compare against correct answer
            if(puzzle.answer.lower() == user_answer.lower()):
                is_correct = True
                response = puzzle.response_string
                logger.info("User %s solved prepuzzle %s." % (str(request.user), prepuzzle_num))
            else:
                is_correct = False
                response = ""
        else:
            is_correct = None
            response = ""
        response_vars = {'response': response, 'is_correct': is_correct}
        return HttpResponse(json.dumps(response_vars))

    else:
        if(not (puzzle.released or request.user.is_staff)):
            return redirect('huntserver:current_hunt_info')
        form = AnswerForm()
        context = {'form': form, 'puzzle': puzzle}
        return HttpResponse(Template(puzzle.template).render(RequestContext(request, context)))


def hunt_prepuzzle(request, hunt_num):
    """
    A simple view that locates the correct prepuzzle for a hunt and redirects there if it exists.
    """
    curr_hunt = get_object_or_404(Hunt, hunt_number=hunt_num)
    if(hasattr(curr_hunt, "prepuzzle")):
        return prepuzzle(request, curr_hunt.prepuzzle.pk)
    else:
        # Maybe we can do something better, but for now, redirect to the main page
        return redirect('huntserver:current_hunt_info')


def current_prepuzzle(request):
    """
    A simple view that locates the correct prepuzzle for the current hunt and redirects to there.
    """
    return hunt_prepuzzle(request, Hunt.objects.get(is_current_hunt=True).hunt_number)


def get_ratelimit_key(group, request):
    return request.ratelimit_key


@method_decorator(csrf_exempt, name='dispatch')
class PuzzleView(View):
    """
    A view to handle answer guesss via POST, handle response update requests via AJAX, and
    render the basic per-puzzle pages.
    """

    def check_rate(self,request, puzzle_id):
        request.puzzle = get_object_or_404(Puzzle, puzzle_id__iexact=puzzle_id)
        request.hunt = request.puzzle.episode.hunt
        request.team = request.hunt.team_from_user(request.user)

        limited = False
        if(request.team is not None):
            request.ratelimit_key = request.team.team_name

            limited = is_ratelimited(request, fn=PuzzleView.as_view(), key='user', rate='20/m', method='POST',
                           increment=True)
        #if (not limited and not request.hunt.is_public):
        #    limited = is_ratelimited(request, fn=PuzzleView.as_view(), key=get_ratelimit_key, rate='5/m', method='POST',
        #                   increment=True)


        return limited or getattr(request, 'limited', False)

    def get(self, request, puzzle_id):
        if self.check_rate(request, puzzle_id):
            logger.info("User %s rate-limited for puzzle %s" % (str(request.user), puzzle_id))
            return HttpResponseForbidden()


        # Only allowed access if the hunt is public or if unlocked by team
        if(not request.hunt.is_public):
            if(not request.user.is_authenticated):
                return redirect('%s?next=%s' % (reverse_lazy(settings.LOGIN_URL), request.path))

            if (not request.user.is_staff):
                if(request.team is None or request.puzzle not in request.team.unlocked.all()):
                    return redirect(reverse('huntserver:hunt', kwargs={'hunt_num' : request.hunt.hunt_number }))

        template = Template(request.puzzle.template).render(RequestContext(request, {'URL' : settings.PROTECTED_URL + "puzzles/" + request.puzzle.puzzle_id }))
        episodes = sorted(request.hunt.get_episodes(request.user, request.team), key=lambda p: p.ep_number)
        puzzles = request.hunt.get_puzzle_list(request.user, request.team)
        context = {'hunt': request.hunt, 'episodes': episodes, 'puzzles' : puzzles, 'puzzle': request.puzzle, 'team': request.team,
            'template':template, 'PROTECTED_URL': settings.PROTECTED_URL}
        return render(request, 'hunt/puzzle.html', context)


    def post(self, request, puzzle_id):
        if self.check_rate(request, puzzle_id):
            logger.info("User %s rate-limited for puzzle %s" % (str(request.user), puzzle_id))
            return JsonResponse({'error': 'too fast'}, status=429)

        team = request.team
        puzzle = request.puzzle
        user = request.user

        # Dealing with answer guesss, proper procedure is to create a guess
        # object and then rely on Guess.respond for automatic responses.
        if(team is None):
            if(puzzle.hunt.is_public):
                team = puzzle.hunt.dummy_team
            else:
                # If the hunt isn't public and you aren't signed in, please stop...
                return JsonResponse({'error':'fail'})


        given_answer = request.POST.get('answer', '')
        if given_answer == '':
            return JsonResponse({'error': 'no answer given'}, status=400)

        guess = Guess(
            guess_text=given_answer,
            team=team,
            user=user,
            puzzle=puzzle,
            guess_time=timezone.now()
        )
        guess.save()
        response = guess.respond()
        if not guess.is_correct:
            now = timezone.now()
            minimum_time = timedelta(seconds=5)

            response['guess'] = given_answer
            response['timeout_length'] = minimum_time.total_seconds() * 1000
            response['timeout_end'] = str(now + minimum_time)
        response['by'] = request.user.username

        return JsonResponse(response)


    def ajax(self, request, puzzle_id):
        # Will return HTML rows for all guesss the user does not yet have
        if(team is None):
            return HttpResponseNotFound('access denied')

        # Find which objects the user hasn't seen yet and render them to HTML
        last_date = datetime.strptime(request.GET.get("last_date"), DT_FORMAT)
        last_date = last_date.replace(tzinfo=tz.gettz('UTC'))
        guesss = Guess.objects.filter(modified_date__gt=last_date)
        guesss = guesss.filter(team=team, puzzle=puzzle)
        guess_list = [render_to_string('puzzle_sub_row.html', {'guess': guess})
                           for guess in guesss]

        try:
            last_date = Guess.objects.latest('modified_date').modified_date.strftime(DT_FORMAT)
        except Guess.DoesNotExist:
            last_date = timezone.now().strftime(DT_FORMAT)

        context = {'guess_list': guess_list, 'last_date': last_date}
        return HttpResponse(json.dumps(context))


@login_required
def unlockables(request):
    """ A view to render the unlockables page for hunt participants. """
    team = Hunt.objects.get(is_current_hunt=True).team_from_user(request.user)
    if(team is None):
        return render(request, 'access_error.html', {'reason': "team"})
    unlockables = Unlockable.objects.filter(puzzle__in=team.solved.all())
    return render(request, 'unlockables.html', {'unlockables': unlockables, 'team': team})
