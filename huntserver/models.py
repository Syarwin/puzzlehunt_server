from django.db import models, transaction
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.utils.dateformat import DateFormat
from dateutil import tz
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
import re
import zipfile
import shutil
from datetime import timedelta

import logging
logger = logging.getLogger(__name__)

time_zone = tz.gettz(settings.TIME_ZONE)


# TODO: cleanup duplicate functions
def get_puzzle_file_path(puzzle, filename):
    return "puzzles/" + puzzle.puzzle_id + "." + filename.split('.')[-1]


def get_solution_file_path(puzzle, filename):
    return "solutions/" + puzzle.puzzle_id + "_sol." + filename.split('.')[-1]


def get_prepuzzle_file_path(prepuzzle, filename):
    return "prepuzzles/" + str(prepuzzle.pk) + "." + filename.split('.')[-1]


def get_hunt_file_path(hunt, filename):
    return "hunt/" + str(hunt.hunt_number) + "." + filename.split('.')[-1]


class PuzzleOverwriteStorage(FileSystemStorage):
    """ A custom storage class that just overwrites existing files rather than erroring """
    def get_available_name(self, name, max_length=None):
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
            extension = name.split('.')[-1]
            folder = "".join(name.split('.')[:-1])
            if(extension == "zip"):
                shutil.rmtree(os.path.join(settings.MEDIA_ROOT, folder), ignore_errors=True)
        return name

    def url(self, name):
        return settings.PROTECTED_URL + name

    def _save(self, name, content):
        rc = super(PuzzleOverwriteStorage, self)._save(name, content)
        extension = name.split('.')[-1]
        folder = "".join(name.split('.')[:-1])
        if(extension == "zip"):
            with zipfile.ZipFile(os.path.join(settings.MEDIA_ROOT, name), "r") as zip_ref:
                zip_ref.extractall(path=os.path.join(settings.MEDIA_ROOT, folder))
        return rc



class Hunt(models.Model):
    """ Base class for a hunt. Contains basic details about a puzzlehunt. """

    class Meta:
        indexes = [
            models.Index(fields=['hunt_number']),
        ]

    hunt_name = models.CharField(
        max_length=200,
        help_text="The name of the hunt as the public will see it")
    hunt_number = models.IntegerField(
        unique=True,
        help_text="A number used internally for hunt sorting, must be unique")
    team_size = models.IntegerField()
    start_date = models.DateTimeField(
        help_text="The date/time at which a hunt will become visible to registered users")
    end_date = models.DateTimeField(
        help_text="The date/time at which a hunt will be archived and available to the public")
    display_start_date = models.DateTimeField(
        help_text="The start date/time displayed to users")
    display_end_date = models.DateTimeField(
        help_text="The end date/time displayed to users")
    resource_file = models.FileField(
        upload_to=get_hunt_file_path,
        storage=PuzzleOverwriteStorage(),
        blank=True,
        help_text="Hunt resources, MUST BE A ZIP FILE.")
    is_current_hunt = models.BooleanField(
        default=False)
    extra_data = models.CharField(
        max_length=200,
        blank=True,
        help_text="A misc. field for any extra data to be stored with the hunt.")
    template = models.TextField(
        default="",
        help_text="The template string to be rendered to HTML on the hunt page")
    points_per_minute = models.IntegerField(
        default=0,
        help_text="The number of points granted per minute during the hunt")
    eureka_feedback = models.CharField(
        max_length=255,
        blank=True,
        help_text="The default feedback message sent when an eureka is found")

    def clean(self, *args, **kwargs):
        """ Overrides the standard clean method to ensure that only one hunt is the current hunt """
        if(not self.is_current_hunt):
            try:
                old_obj = Hunt.objects.get(pk=self.pk)
                if(old_obj.is_current_hunt):
                    raise ValidationError({'is_current_hunt':
                                           ["There must always be one current hunt", ]})
            except ObjectDoesNotExist:
                pass
        super(Hunt, self).clean(*args, **kwargs)

    @transaction.atomic
    def save(self, *args, **kwargs):
        """ Overrides the standard save method to ensure that only one hunt is the current hunt """
        self.full_clean()
        if self.is_current_hunt:
            Hunt.objects.filter(is_current_hunt=True).update(is_current_hunt=False)
        super(Hunt, self).save(*args, **kwargs)

    @property
    def is_locked(self):
        """ A boolean indicating whether or not the hunt is locked """
        return timezone.now() < self.start_date

    @property
    def is_open(self):
        """ A boolean indicating whether or not the hunt is open to registered participants """
        return timezone.now() >= self.start_date and timezone.now() < self.end_date

    @property
    def is_public(self):
        """ A boolean indicating whether or not the hunt is open to the public """
        return timezone.now() > self.end_date

    @property
    def is_day_of_hunt(self):
        """ A boolean indicating whether or not today is the day of the hunt """
        return timezone.now().date() == self.start_date.date()

    @property
    def in_reg_lockdown(self):
        """ A boolean indicating whether or not registration has locked for this hunt """
        return (self.start_date - timezone.now()).days <= settings.HUNT_REGISTRATION_LOCKOUT

    @property
    def season(self):
        """ Gets a season string from the hunt dates """
        if(self.start_date.month >= 1 and self.start_date.month <= 5):
            return "Spring"
        elif(self.start_date.month >= 8 and self.start_date.month <= 12):
            return "Fall"
        else:
            return "Summer"

    @property
    def real_teams(self):
        """ A queryset of all non-dummy teams in the hunt """
        return self.team_set.exclude(location="DUMMY").all()

    @property
    def dummy_team(self):
        """ The dummy team for the hunt, useful once the hunt is over """
        try:
            team = self.team_set.get(location="DUMMY")
        except Team.DoesNotExist:
            team = Team.objects.create(team_name=self.hunt_name + "_DUMMY", hunt=self,
                                       location="DUMMY", join_code="WRONG")
        return team

    def __str__(self):
        if(self.is_current_hunt):
            return self.hunt_name + " (c)"
        else:
            return self.hunt_name

    def team_from_user(self, user):
        """ Takes a user and a hunt and returns either the user's team for that hunt or None """
        if(not user.is_authenticated):
            return None
        teams = get_object_or_404(Person, user=user).teams.filter(hunt=self)
        return teams[0] if (len(teams) > 0) else None

    def can_access(self, user, team):
        return self.is_public or user.is_staff or (team and team.is_playtester_team and team.playtest_started)

    def get_episodes(self, user, team):
        if (self.is_public or user.is_staff):
            episode_list = self.episode_set.all()
        else:
            episode_list = self.episode_set.filter(start_date__lte=timezone.now())

        return episode_list

    def get_puzzle_list(self, user, team):
        if (self.is_public or user.is_staff):
            puzzle_list = [puzzle for episode in self.episode_set.all() for puzzle in episode.puzzle_set.all()]

        elif(team and team.is_playtester_team and team.playtest_started):
            puzzle_list = team.unlocked.filter(episode__hunt=self)
        else:
            puzzle_list = ()

        return puzzle_list



class Episode(models.Model):
    """ Base class for a set of puzzle """

    class Meta:
        indexes = [
            models.Index(fields=['ep_number']),
        ]

    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that this episode is a part of")
    ep_name = models.CharField(
        max_length=200,
        help_text="The name of the episode as the public will see it")
    ep_number = models.IntegerField(
        unique=True,
        help_text="A number used internally for hunt sorting, must be unique")
    start_date = models.DateTimeField(
        help_text="The date/time at which a hunt will become visible to registered users")

    @property
    def is_locked(self):
        """ A boolean indicating whether or not the ep is locked """
        return timezone.now() < self.start_date

    @property
    def is_open(self):
        """ A boolean indicating whether or not the ep is open"""
        return timezone.now() >= self.start_date

    def __str__(self):
        return self.ep_name

"""
            if (hunt.is_public or request.user.is_staff):
                puzzle_list = hunt.puzzle_set.all()

            elif(team and team.is_playtester_team and team.playtest_started):
                puzzle_list = team.unlocked.filter(hunt=hunt)

            # Hunt has not yet started
            elif(hunt.is_locked):
                if(hunt.is_day_of_hunt):
                    return render(request, 'access_error.html', {'reason': "hunt"})
                else:
                    return hunt_prepuzzle(request, hunt_num)
"""




class Puzzle(models.Model):
    """ A class representing a puzzle within a hunt """

    class Meta:
        indexes = [
            models.Index(fields=['puzzle_id']),
        ]
        ordering = ['-episode', 'puzzle_number']

    SOLVES_UNLOCK = 'SOL'
    POINTS_UNLOCK = 'POT'
    EITHER_UNLOCK = 'ETH'
    BOTH_UNLOCK = 'BTH'

    puzzle_unlock_type_choices = [
        (SOLVES_UNLOCK, 'Solves Based Unlock'),
        (POINTS_UNLOCK, 'Points Based Unlock'),
        (EITHER_UNLOCK, 'Either (OR) Unlocking Method'),
        (BOTH_UNLOCK, 'Both (AND) Unlocking Methods'),
    ]

    PDF_PUZZLE = 'PDF'
    LINK_PUZZLE = 'LNK'
    WEB_PUZZLE = 'WEB'

    puzzle_page_type_choices = [
        (PDF_PUZZLE, 'Puzzle page displays a PDF'),
        (LINK_PUZZLE, 'Puzzle page links a webpage'),
        (WEB_PUZZLE, 'Puzzle page displays a webpage'),
    ]

    episode = models.ForeignKey(
        Episode,
        on_delete=models.CASCADE,
        help_text="The episode that this puzzle is a part of")
    puzzle_name = models.CharField(
        max_length=200,
        help_text="The name of the puzzle as it will be seen by hunt participants")
    puzzle_number = models.IntegerField(
        help_text="The number of the puzzle within the episode, for sorting purposes")
    puzzle_id = models.CharField(
        max_length=12,
        unique=True,  # hex only please
        help_text="A 3-12 character hex string that uniquely identifies the puzzle")
    answer = models.CharField(
        max_length=100,
        help_text="The answer to the puzzle, not case sensitive")
    answer_regex = models.CharField(
        max_length=100,
        help_text="The regexp towards which the guess is checked in addition to the answer (optional)",
        default= "")
    is_meta = models.BooleanField(
        default=False,
        verbose_name="Is a metapuzzle",
        help_text="Is this puzzle a meta-puzzle?")
    puzzle_page_type = models.CharField(
        max_length=3,
        choices=puzzle_page_type_choices,
        default=WEB_PUZZLE,
        blank=False,
        help_text="The type of webpage for this puzzle."
    )
    doesnt_count = models.BooleanField(
        default=False,
        help_text="Should this puzzle not count towards scoring?")
    puzzle_file = models.FileField(
        upload_to=get_puzzle_file_path,
        storage=PuzzleOverwriteStorage(),
        blank=True,
        help_text="Puzzle file. MUST BE A PDF")
    resource_file = models.FileField(
        upload_to=get_puzzle_file_path,
        storage=PuzzleOverwriteStorage(),
        blank=True,
        help_text="Puzzle resources, MUST BE A ZIP FILE.")
    template = models.TextField(
        default="",
        help_text="The template string to be rendered to HTML on the puzzle page")
    solution_is_webpage = models.BooleanField(
        default=False,
        help_text="Is this solution an html webpage?")
    solution_file = models.FileField(
        upload_to=get_solution_file_path,
        storage=PuzzleOverwriteStorage(),
        blank=True,
        help_text="Puzzle solution. MUST BE A PDF.")
    solution_resource_file = models.FileField(
        upload_to=get_solution_file_path,
        storage=PuzzleOverwriteStorage(),
        blank=True,
        help_text="Puzzle solution resources, MUST BE A ZIP FILE.")
    extra_data = models.CharField(
        max_length=200,
        blank=True,
        help_text="A misc. field for any extra data to be stored with the puzzle.")

    # Unlocking:
    unlock_type = models.CharField(
        max_length=3,
        choices=puzzle_unlock_type_choices,
        default=SOLVES_UNLOCK,
        blank=False,
        help_text="The type of puzzle unlocking scheme"
    )
    num_required_to_unlock = models.IntegerField(
        default=1,
        help_text="Number of prerequisite puzzles that need to be solved to unlock this puzzle")
    unlocks = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        help_text="Puzzles that this puzzle is a possible prerequisite for")
    points_cost = models.IntegerField(
        default=0,
        help_text="The number of points needed to unlock this puzzle.")
    points_value = models.IntegerField(
        default=0,
        help_text="The number of points this puzzle grants upon solving.")

    # Overridden to delete old files on clear
    def save(self, *args, **kwargs):
        if(self.pk):
            # TODO: Clean up this repetitive code
            old_obj = Puzzle.objects.get(pk=self.pk)
            if(self.puzzle_file.name == "" and old_obj.puzzle_file.name != ""):
                full_name = os.path.join(settings.MEDIA_ROOT, old_obj.puzzle_file.name)
                extension = old_obj.puzzle_file.name.split('.')[-1]
                folder = "".join(old_obj.puzzle_file.name.split('.')[:-1])
                if(extension == "zip"):
                    shutil.rmtree(os.path.join(settings.MEDIA_ROOT, folder), ignore_errors=True)
                if os.path.exists(full_name):
                    os.remove(full_name)
            if(self.resource_file.name == "" and old_obj.resource_file.name != ""):
                full_name = os.path.join(settings.MEDIA_ROOT, old_obj.resource_file.name)
                extension = old_obj.resource_file.name.split('.')[-1]
                folder = "".join(old_obj.resource_file.name.split('.')[:-1])
                if(extension == "zip"):
                    shutil.rmtree(os.path.join(settings.MEDIA_ROOT, folder), ignore_errors=True)
                if os.path.exists(full_name):
                    os.remove(full_name)
            if(self.solution_file.name == "" and old_obj.solution_file.name != ""):
                full_name = os.path.join(settings.MEDIA_ROOT, old_obj.solution_file.name)
                extension = old_obj.solution_file.name.split('.')[-1]
                folder = "".join(old_obj.solution_file.name.split('.')[:-1])
                if(extension == "zip"):
                    shutil.rmtree(os.path.join(settings.MEDIA_ROOT, folder), ignore_errors=True)
                if os.path.exists(full_name):
                    os.remove(full_name)
            old_name = old_obj.solution_resource_file.name
            if(self.solution_resource_file.name == "" and old_name != ""):
                full_name = os.path.join(settings.MEDIA_ROOT, old_obj.solution_resource_file.name)
                extension = old_obj.solution_resource_file.name.split('.')[-1]
                folder = "".join(old_obj.solution_resource_file.name.split('.')[:-1])
                if(extension == "zip"):
                    shutil.rmtree(os.path.join(settings.MEDIA_ROOT, folder), ignore_errors=True)
                if os.path.exists(full_name):
                    os.remove(full_name)

        super(Puzzle, self).save(*args, **kwargs)

    def serialize_for_ajax(self):
        """ Serializes the ID, puzzle_number and puzzle_name fields for ajax transmission """
        message = dict()
        message['id'] = self.puzzle_id
        message['number'] = self.puzzle_number
        message['name'] = self.puzzle_name
        return message

    @property
    def safename(self):
        name = self.puzzle_name.lower().replace(" ", "_")
        return re.sub(r'[^a-z_]', '', name)

    def __str__(self):
        return str(self.puzzle_number) + "-" + str(self.puzzle_id) + " " + self.puzzle_name

    def starting_time_for_team(self, team):
        episode = self.episode
        if team is None:
            return episode.start_date
        else:
            try:
                unlock = PuzzleUnlock.objects.get(puzzle=self, team=team)
                return unlock.time
            except PuzzleUnlock.DoesNotExist:
                try:
                    guess = Guess.objects.filter(puzzle=self, team=team).order_by("guess_time").first()
                    if guess is None:
                       return episode.start_date
                    else:
                       return guess.guess_time
                except Guess.DoesNotExist:
                    return episode.start_date



class Prepuzzle(models.Model):
    """ A class representing a pre-puzzle within a hunt """

    puzzle_name = models.CharField(
        max_length=200,
        help_text="The name of the puzzle as it will be seen by hunt participants")
    released = models.BooleanField(
        default=False)
    hunt = models.OneToOneField(
        Hunt,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="The hunt that this puzzle is a part of, leave blank for no associated hunt.")
    answer = models.CharField(
        max_length=100,
        help_text="The answer to the puzzle, not case sensitive")
    template = models.TextField(
        default='{% extends "prepuzzle.html" %}\r\n{% load prepuzzle_tags %}\r\n' +
                '\r\n{% block content %}\r\n{% endblock content %}',
        help_text="The template string to be rendered to HTML on the hunt page")
    resource_file = models.FileField(
        upload_to=get_prepuzzle_file_path,
        storage=PuzzleOverwriteStorage(),
        blank=True,
        help_text="Prepuzzle resources, MUST BE A ZIP FILE.")
    response_string = models.TextField(
        default="",
        help_text="Data returned to the webpage for use upon solving.")

    def __str__(self):
        if(self.hunt):
            return "prepuzzle " + str(self.pk) + " (" + str(self.hunt.hunt_name) + ")"
        else:
            return "prepuzzle " + str(self.pk)

    # Overridden to delete old files on clear
    def save(self, *args, **kwargs):
        if(self.resource_file.name == ""):
            old_obj = Prepuzzle.objects.get(pk=self.pk)
            if(old_obj.resource_file.name != ""):
                extension = old_obj.resource_file.name.split('.')[-1]
                folder = "".join(old_obj.resource_file.name.split('.')[:-1])
                if(extension == "zip"):
                    shutil.rmtree(os.path.join(settings.MEDIA_ROOT, folder), ignore_errors=True)
                if os.path.exists(os.path.join(settings.MEDIA_ROOT, old_obj.resource_file.name)):
                    os.remove(os.path.join(settings.MEDIA_ROOT, old_obj.resource_file.name))
        super(Prepuzzle, self).save(*args, **kwargs)


class TeamManager(models.Manager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (models.Q(team_name__icontains=query) |
                         models.Q(location__icontains=query))
            qs = qs.filter(or_lookup).distinct()
        return qs


class Eureka(models.Model):
    """ A class to represent an automated response regex """

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this automated response is related to")
    regex = models.CharField(
        max_length=400,
        help_text="The python-style regex that will be checked against the user's response")
    answer = models.CharField(
        max_length=400,
        help_text="The text to use in the guess response if the regex matched")
    feedback = models.CharField(
        max_length=255,
        blank=True,
        help_text="The feedback message sent when this eureka is found - if blank, use the default feedback of the hunt")

    def __str__(self):
        return self.answer + " (" + self.regex + ")=> " + self.feedback

    @property
    def get_feedback(self):
        if self.feedback != '':
            return self.feedback
        else:
            return self.puzzle.episode.hunt.eureka_feedback


class Team(models.Model):
    """ A class representing a team within a hunt """

    team_name = models.CharField(
        max_length=200,
        help_text="The team name as it will be shown to hunt participants")
    location = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        help_text="The country the members of the team are from")
    solved = models.ManyToManyField(
        Puzzle,
        blank=True,
        related_name='solved_for',
        through="PuzzleSolve",
        help_text="The puzzles the team has solved")
    unlocked = models.ManyToManyField(
        Puzzle,
        blank=True,
        related_name='unlocked_for',
        through="PuzzleUnlock",
        help_text="The puzzles the team has unlocked")
    eurekas = models.ManyToManyField(
        Eureka,
        blank=True,
        related_name='eurekas_for',
        through="EurekaUnlock",
        help_text="The eurekas the team has unlocked")
    unlockables = models.ManyToManyField(
        "Unlockable",
        blank=True,
        help_text="The unlockables the team has earned")
    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that the team is a part of")
    join_code = models.CharField(
        max_length=5,
        help_text="The 5 character random alphanumeric password needed for a user to join a team")
    playtester = models.BooleanField(
        default=False,
        help_text="A boolean to indicate if the team is a playtest team and will get early access")
    playtest_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date/time at which a hunt will become to the playtesters")
    playtest_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date/time at which a hunt will no longer be available to playtesters")
    num_waiting_messages = models.IntegerField(
        default=0,
        help_text="The number of unseen messages a team has waiting")
    num_unlock_points = models.IntegerField(
        default=0,
        help_text="The number of points the team has earned")

    objects = TeamManager()

    @property
    def is_playtester_team(self):
        """ A boolean indicating whether or not the team is a playtesting team """
        return self.playtester

    @property
    def playtest_started(self):
        """ A boolean indicating whether or not the team is currently allowed to be playtesting """
        if(self.playtest_start_date is None or self.playtest_end_date is None):
            return False
        return (timezone.now() >= self.playtest_start_date)

    @property
    def playtest_over(self):
        """ A boolean indicating whether or not the team's playtest slot has passed """
        if(self.playtest_start_date is None or self.playtest_end_date is None):
            return False
        return timezone.now() >= self.playtest_end_date

    @property
    def playtest_happening(self):
        """ A boolean indicating whether or not the team's playtest slot is currently happening """
        return self.playtest_started and not self.playtest_over

    @property
    def is_normal_team(self):
        """ A boolean indicating whether or not the team is a normal (non-playtester) team """
        return (not self.playtester)

    @property
    def short_name(self):
        """ Team name shortened to 30 characters for more consistent display """
        if(len(self.team_name) > 30):
            return self.team_name[:30] + "..."
        else:
            return self.team_name

    @property
    def size(self):
        """ The number of people on the team """
        return self.person_set.count()

    def unlock_puzzles(self):
        """ Unlocks all puzzles a team is currently supposed to have unlocked """
        puzzles = self.hunt.puzzle_set.all().order_by('puzzle_number')
        numbers = []

        numbers = puzzles.values_list('puzzle_number', flat=True)
        # make an array for how many points a team has towards unlocking each puzzle
        mapping = [0 for i in range(max(numbers) + 1)]

        # go through each solved puzzle and add to the list for each puzzle it unlocks
        for puzzle in self.solved.all():
            for num in puzzle.unlocks.values_list('puzzle_number', flat=True):
                mapping[num] += 1

        # See if the number of points is enough to unlock any given puzzle
        puzzles = puzzles.difference(self.unlocked.all())
        for puzzle in puzzles:
            s_unlock = (puzzle.num_required_to_unlock <= mapping[puzzle.puzzle_number])
            p_unlock = (self.num_unlock_points >= puzzle.points_cost)

            if(puzzle.unlock_type == Puzzle.SOLVES_UNLOCK and s_unlock):
                logger.info("Team %s unlocked puzzle %s with solves" % (str(self.team_name),
                            str(puzzle.puzzle_id)))
                PuzzleUnlock.objects.create(team=self, puzzle=puzzle, time=timezone.now())
            elif(puzzle.unlock_type == Puzzle.POINTS_UNLOCK and p_unlock):
                logger.info("Team %s unlocked puzzle %s with points" % (str(self.team_name),
                            str(puzzle.puzzle_id)))
                PuzzleUnlock.objects.create(team=self, puzzle=puzzle, time=timezone.now())
            elif(puzzle.unlock_type == Puzzle.EITHER_UNLOCK and (s_unlock or p_unlock)):
                logger.info("Team %s unlocked puzzle %s with either" % (str(self.team_name),
                            str(puzzle.puzzle_id)))
                PuzzleUnlock.objects.create(team=self, puzzle=puzzle, time=timezone.now())
            elif(puzzle.unlock_type == Puzzle.BOTH_UNLOCK and (s_unlock and p_unlock)):
                logger.info("Team %s unlocked puzzle %s with both" % (str(self.team_name),
                            str(puzzle.puzzle_id)))
                PuzzleUnlock.objects.create(team=self, puzzle=puzzle, time=timezone.now())

    def reset(self):
        """ Resets/deletes all of the team's progress """
        self.unlocked.clear()
        self.puzzlesolve_set.all().delete()
        self.solved.clear()
        self.guess_set.all().delete()
        self.num_unlock_points = 0
        self.save()

    def __str__(self):
        return str(self.size) + " (" + str(self.location) + ") " + self.short_name


class PersonManager(models.Manager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (models.Q(user__username__icontains=query) |
                         models.Q(user__first_name__icontains=query) |
                         models.Q(user__last_name__icontains=query) |
                         models.Q(user__email__icontains=query))
            qs = qs.filter(or_lookup).distinct()
        return qs



class Person(models.Model):
    """ A class to associate more personal information with the default django auth user class """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        help_text="The corresponding user to this person")
    comments = models.CharField(
        max_length=400,
        blank=True,
        help_text="Comments or other notes about the person")
    teams = models.ManyToManyField(
        Team,
        blank=True,
        help_text="Teams that the person is on")

    objects = PersonManager()

    def __str__(self):
        name = self.user.first_name + " " + self.user.last_name + " (" + self.user.username + ")"
        if(name == "  ()"):
            return "Anonymous User"
        else:
            return name


class Guess(models.Model):
    """ A class representing a guess to a given puzzle from a given team """

    class Meta:
        verbose_name_plural = 'Guesses'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The user that made the guess")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that made the guess")
    guess_time = models.DateTimeField()
    guess_text = models.CharField(
        max_length=100)
    response_text = models.CharField(
        blank=True,
        max_length=400,
        help_text="Response to the given answer. Empty string indicates human response needed")
    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this guess is in response to")
    modified_date = models.DateTimeField(
        help_text="Last date/time of response modification")

    def serialize_for_ajax(self):
        """ Serializes the time, puzzle, team, and status fields for ajax transmission """
        message = dict()
        df = DateFormat(self.guess_time.astimezone(time_zone))
        message['time_str'] = df.format("h:i a")
        message['puzzle'] = self.puzzle.serialize_for_ajax()
        message['team_pk'] = self.team.pk
        message['status_type'] = "guess"
        return message

    @property
    def is_correct(self):
        """ A boolean indicating if the guess given is exactly correct """
        noSpace = self.guess_text.upper().replace(" ","")
        
        return (noSpace == self.puzzle.answer.upper().replace(" ","") or (self.puzzle.answer_regex != "" and re.fullmatch(self.puzzle.answer_regex, noSpace, re.IGNORECASE)))

    @property
    def convert_markdown_response(self):
        """ The response with all markdown links converted to HTML links """
        return re.sub(r'\[(.*?)\]\((.*?)\)', '<a href="\\2">\\1</a>', self.response_text)

    def save(self, *args, **kwargs):
        """ Overrides the default save function to update the modified date on save """
        self.modified_date = timezone.now()
        super(Guess, self).save(*args, **kwargs)

    def create_solve(self):
        """ Creates a solve based on this guess """
        PuzzleSolve.objects.create(puzzle=self.puzzle, team=self.team, guess=self)
        logger.info("Team %s correctly solved puzzle %s" % (str(self.team.team_name),
                                                            str(self.puzzle.puzzle_id)))

    # Automatic guess response system
    # Returning an empty string means that huntstaff should respond via the queue
    # Order of response importance: Regex, Defaults, Staff response.
    def respond(self):
        """ Takes the guess's text and uses various methods to craft and populate a response.
            If the response is correct a solve is created and the correct puzzles are unlocked"""
      
        noSpace = self.guess_text.upper().replace(" ","")
        # Compare against correct answer
        if(self.is_correct):
            # Make sure we don't have duplicate or after hunt guess objects
            if(not self.puzzle.episode.hunt.is_public):
                if(self.puzzle not in self.team.solved.all()):
                    self.create_solve()
                    t = self.team
                    t.num_unlock_points = models.F('num_unlock_points') + self.puzzle.points_value
                    t.save()
                    t.refresh_from_db()
                    t.unlock_puzzles()

            return {"status": "correct", "message": "Correct!"}

        else:
            # TODO removed unlocked Eureka
            for resp in self.puzzle.eureka_set.all():
                if(re.fullmatch(resp.regex, noSpace, re.IGNORECASE)):
                    if(resp not in self.team.eurekas.all()):
                        EurekaUnlock.objects.create(team=self.team, eureka=resp, time=timezone.now())
                    return {"status": "eureka", "message": resp.get_feedback}
            else:  # Give a default response if no regex matches
                # Current philosphy is to auto-can wrong answers: If it's not right, it's wrong
                return {"status" : "wrong", "message" : "Wrong Answer" }


    def update_response(self, text):
        """ Updates the response with the given text """
        self.response_text = text
        self.modified_date = timezone.now()  # TODO: I think this line is useless because of ^ save
        self.save()

    def __str__(self):
        return self.guess_text



class PuzzleSolve(models.Model):
    """ A class that links a team and a puzzle to indicate that the team has solved the puzzle """

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this is a solve for")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that this solve is from")
    guess = models.ForeignKey(
        Guess,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The guess object that the team submitted to solve the puzzle")

    class Meta:
        unique_together = ('puzzle', 'team',)

    def serialize_for_ajax(self):
        """ Serializes the puzzle, team, time, and status fields for ajax transmission """
        message = dict()
        message['puzzle'] = self.puzzle.serialize_for_ajax()
        message['team_pk'] = self.team.pk
        time = self.guess.guess_time
        df = DateFormat(time.astimezone(time_zone))
        message['time_str'] = df.format("h:i a")
        message['status_type'] = "solve"
        return message

    def __str__(self):
        return self.team.short_name + " => " + self.puzzle.puzzle_name



class PuzzleUnlock(models.Model):
    """ A class that links a team and a puzzle to indicate that the team has unlocked the puzzle """

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this is an unlock for")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that this unlocked puzzle is for")
    time = models.DateTimeField(
        help_text="The time this puzzle was unlocked for this team")

    class Meta:
        unique_together = ('puzzle', 'team',)

    def serialize_for_ajax(self):
        """ Serializes the puzzle, team, and status fields for ajax transmission """
        message = dict()
        message['puzzle'] = self.puzzle.serialize_for_ajax()
        message['team_pk'] = self.team.pk
        message['status_type'] = "unlock"
        return message

    def __str__(self):
        return self.team.short_name + ": " + self.puzzle.puzzle_name



class Unlockable(models.Model):
    """ A class that represents an object to be unlocked after solving a puzzle """

    TYPE_CHOICES = (
        ('IMG', 'Image'),
        ('PDF', 'PDF'),
        ('TXT', 'Text'),
        ('WEB', 'Link'),
    )
    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that needs to be solved to unlock this object")
    content_type = models.CharField(
        max_length=3,
        choices=TYPE_CHOICES,
        default='TXT',
        help_text="The type of object that is to be unlocked, can be 'IMG', 'PDF', 'TXT', or 'WEB'")
    content = models.CharField(
        max_length=500,
        help_text="The link to the content, files must be externally hosted.")

    def __str__(self):
        return "%s (%s)" % (self.puzzle.puzzle_name, self.content_type)




class EurekaUnlock(models.Model):
    """ A class that links a team and a eureka to indicate that the team has unlocked the eureka """

    eureka = models.ForeignKey(
        Eureka,
        on_delete=models.CASCADE,
        help_text="The eureka unlocked")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that this unlocked puzzle is for")
    time = models.DateTimeField(
        help_text="The time this eureka was unlocked for this team")

    class Meta:
        unique_together = ('eureka', 'team',)

    def serialize_for_ajax(self):
        """ Serializes the puzzle, team, and status fields for ajax transmission """
        message = dict()
        message['eureka'] = self.eureka.pk
        message['team_pk'] = self.team.pk
        message['status_type'] = "unlock"
        return message

    def __str__(self):
        return self.team.short_name + ": " + self.eureka.answer



class Hint(models.Model):
    """ A class to represent an hint """

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this automated response is related to")
    text = models.CharField(
        max_length=400,
        help_text="The text to display")
    time = models.DurationField(
        verbose_name='Delay',
        help_text=('Time after anyone on the team first loads the puzzle'),
        validators=(MinValueValidator(timedelta(seconds=0)),),
    )
    eurekas = models.ManyToManyField(
        'Eureka',
        verbose_name='Eureka conditions',
        blank=True,
        help_text="Eurekas that are a prerequisite for shorter time"
    )
    short_time =  models.DurationField(
        verbose_name='Shorter Delay',
        help_text=('Time after all the associated Eurekas were found'),
        validators=(MinValueValidator(timedelta(seconds=0)),),
    )

    def __str__(self):
        return str(self.time) + " => " + self.text


    @property
    def compact_id(self):
        return self.id

    def unlocks_at(self, team):
        """Returns when the hint unlocks for the given team.

        Parameters as for `unlocked_by`.
        """
        # TODO
        return timezone.now() + self.time

    def delay_for_team(self, team):
        """Returns how long until the hint unlocks for the given team.

        Parameters as for `unlocked_by`.
        """
        if team is None:
            return self.time
        else:
            if self.eurekas.all().count() > 0:
                for eureka in self.eurekas.all():
                    if not eureka in team.eurekas.all():
                        return self.time
                return self.short_time
            else:
                return self.time

    def starting_time_for_team(self, team):
        return self.puzzle.starting_time_for_team(team)



class OverwriteStorage(FileSystemStorage):
    """ A custom storage class that just overwrites existing files rather than erroring """
    def get_available_name(self, name, max_length=None):
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name



class HuntAssetFile(models.Model):
    """ A class to represent an asset file for a puzzlehunt """
    file = models.FileField(upload_to='hunt/assets/', storage=OverwriteStorage())

    def __str__(self):
        return os.path.basename(self.file.name)
