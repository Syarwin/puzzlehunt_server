from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.db import models, transaction
from datetime import timedelta
from teams.models import Team, Person, Guess, TeamPuzzleLink

import os
import re
import zipfile
import shutil
import logging
logger = logging.getLogger(__name__)


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


class OverwriteStorage(FileSystemStorage):
    """ A custom storage class that just overwrites existing files rather than erroring """
    def get_available_name(self, name, max_length=None):
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name


class Hunt(models.Model):
    """ Base class for a hunt. Contains basic details about a puzzlehunt. """

    class Meta:
        verbose_name_plural = "    Hunts"
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
        verbose_name_plural = "   Episodes"
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
        help_text="A number used internally for episode sorting, must be unique")
    start_date = models.DateTimeField(
        help_text="The date/time at which this episode will become visible to registered users (without headstarts)")

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

class PuzzleManager(models.Manager):
    """ Manager to reorder correctly puzzles within an episode """

    def reorder(self, puz, old_number, old_episode):
        """ Reorder the puzzles after a change of number/episode for puz """
        
        qs = self.get_queryset()
        num_puzzles = len(puz.episode.puzzle_set.all())
        ep_changed = (puz.episode.ep_number!=old_episode.ep_number)

        # If necessary, we clip the value of puzzle_number
        if puz.puzzle_number>num_puzzles:
            puz.puzzle_number = num_puzzles+1 if ep_changed else num_puzzles
            puz.save()
        if puz.puzzle_number<1:
            puz.puzzle_number = 1
            puz.save()

        with transaction.atomic():
            puz_number = puz.puzzle_number
            if ep_changed:
                # If the episode was changed, we first reorder the old episode, and then
                # reorder the new one by assuming that puz was added at the end
                qs.filter(episode=old_episode, puzzle_number__gt=old_number) \
                    .exclude(pk=puz.pk) \
                    .update(puzzle_number=models.F('puzzle_number') - 1)
                old_number = num_puzzles+1

            # Reordering in the new episode depends on whether puz should be moved up or down
            if puz_number < int(old_number):
                qs.filter(episode=puz.episode, puzzle_number__lt=old_number, puzzle_number__gte=puz_number) \
                    .exclude(pk=puz.pk) \
                    .update(puzzle_number=models.F('puzzle_number') + 1)
            else:
                qs.filter(episode=puz.episode, puzzle_number__lte=puz_number, puzzle_number__gt=old_number) \
                    .exclude(pk=puz.pk) \
                    .update(puzzle_number=models.F('puzzle_number') - 1)


class Puzzle(models.Model):
    """ A class representing a puzzle within a hunt """

    class Meta:
        verbose_name_plural = "  Puzzles"
        indexes = [
            models.Index(fields=['puzzle_id']),
        ]
        ordering = ['-episode', 'puzzle_number']

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
        default=1,
        help_text="The number of the puzzle within the episode, for sorting purposes (must be unique within the episode, and not too large)")
    puzzle_id = models.CharField(
        max_length=12,
        unique=True,  # hex only please
        help_text="A 3-12 character hex string that uniquely identifies the puzzle")
    answer = models.CharField(
        max_length=100,
        help_text="The answer to the puzzle, not case nor space sensitive. Can contain parentheses to show multiple options but a regex is then mandatory.")
    answer_regex = models.CharField(
        max_length=100,
        help_text="The regexp towards which the guess is checked in addition to the answer (optional)",
        blank=True,
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

    num_required_to_unlock = models.IntegerField(
        default=1,
        help_text="Number of prerequisite puzzles that need to be solved to unlock this puzzle")
    unlocks = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        help_text="Puzzles that this puzzle is a possible prerequisite for")

    objects = PuzzleManager()

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
                unlock = TeamPuzzleLink.objects.get(puzzle=self, team=team)
                return unlock.time
            except TeamPuzzleLink.DoesNotExist:
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
        default='{% extends "puzzle/prepuzzle.html" %}\r\n{% load prepuzzle_tags %}\r\n' +
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


class Eureka(models.Model):
    """ A class to represent an automated response regex """
    class Meta:
        verbose_name_plural = " Eurekas"

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


class Hint(models.Model):
    """ A class to represent an hint """
    class Meta:
        verbose_name_plural = "Hints"

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



class HuntAssetFile(models.Model):
    """ A class to represent an asset file for a puzzlehunt """
    file = models.FileField(upload_to='hunt/assets/', storage=OverwriteStorage())

    def __str__(self):
        return os.path.basename(self.file.name)



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
