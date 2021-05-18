from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.contrib.postgres.fields import ArrayField
from datetime import timedelta
from teams.models import Team, Person, Guess, TeamPuzzleLink, TeamEpisodeLink

import os
import re
import zipfile
import shutil
import uuid
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
        help_text="The date/time at which the hunt page will become visible to registered users")
    end_date = models.DateTimeField(
        help_text="The date/time at which a hunt will be archived and available to the public / stats will be released")
    display_start_date = models.DateTimeField(
        help_text="The start date/time displayed to users")
    display_end_date = models.DateTimeField(
        help_text="The end date/time displayed to users")
    is_current_hunt = models.BooleanField(
        default=False)
    is_demo = models.BooleanField(
        default=False,
        help_text="If yes, then all puzzles are available to everybody as prepuzzles (and hints / eurekas do not work)")
    eureka_feedback = models.CharField(
        max_length=255,
        blank=True,
        help_text="The default feedback message sent when an eureka is found")
    discord_url = models.URLField(
        blank=True,
        default='',
        help_text="URL of the discord server, leave empty is none is dedicated to the hunt")
    discord_bot_id = models.BigIntegerField(
        null=True,
        blank=True,
        default='0',
        help_text="Dicord bot id, leave blank or zero if none is dedicated to the hunt")
    template = models.TextField(
        default="",
        null=True,
        blank=True,
        help_text="The template string to be rendered to HTML on the puzzle page")


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
        return timezone.now() >= self.end_date or self.is_demo

    @property
    def is_day_of_hunt(self):
        """ A boolean indicating whether or not today is the day of the hunt """
        return timezone.now().date() == self.display_start_date.date()

    @property
    def in_reg_lockdown(self):
        """ A boolean indicating whether or not registration has locked for this hunt """
        return False #(self.start_date - timezone.now()).days <= settings.HUNT_REGISTRATION_LOCKOUT

    def __str__(self):
        if(self.is_current_hunt):
            return self.hunt_name + " (c)"
        else:
            return self.hunt_name

    def team_from_user(self, user):
        """ Takes a user and a hunt and returns either the user's team for that hunt or None """
        if(not user.is_authenticated):
            return None
        try:
            teams = Person.objects.get(user=user).teams.filter(hunt=self)
            return teams[0] if (len(teams) > 0) else None
        except Person.DoesNotExist:
            return None

    def can_access(self, user, team):
        return self.is_public or user.is_staff or (team and (self.is_open or (team.is_playtester_team and team.playtest_started)))

    def get_episodes(self, user, team):
        """ Return the list of episodes that a user/team can see"""
        if (user.is_staff or self.is_public):
            episode_list = self.episode_set.order_by('ep_number').all()
        else:
            episode_pks = TeamEpisodeLink.objects \
                .filter(team=team, episode__start_date__lte=timezone.now()+F("headstart")) \
                .values_list('episode', flat=True)
            episode_list = Episode.objects.filter(pk__in=episode_pks).order_by('ep_number')

        return episode_list

    def get_formatted_episodes(self, user, team):
#        episodes = sorted(self.get_episodes(user, team), key=lambda p: p.ep_number)
        episodes = self.get_episodes(user,team)
        if user.is_staff or self.is_public:
            episodes = [{'ep': ep, 'puz': ep.puzzle_set.all(), 'solves': 0} for ep in episodes]
        else:
            episodes = [{'ep': ep, 'puz': team.puz_unlocked.filter(episode=ep), 'solves':0} for ep in episodes]
        if team is not None:
            for i in range(len(episodes)):
                episodes[i]['solves'] = team.puz_solved.filter(episode=episodes[i]['ep']).count()
        return episodes

    def get_puzzle_list(self, user, team):
        """ Return the list of puzzles that a user/team can see"""
        if (user.is_staff):
            puzzle_list = [puzzle for episode in self.episode_set.all() for puzzle in episode.puzzle_set.all()]
        elif(self.can_access(user, team)):
            puzzle_list = team.puz_unlocked.filter(episode__hunt=self)
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
        ordering = ['ep_number']

    ep_name = models.CharField(
        max_length=200,
        help_text="The name of the episode as the public will see it")
    ep_number = models.IntegerField(
        unique=True,
        help_text="A number used internally for episode sorting, must be unique")
    start_date = models.DateTimeField(
        help_text="The date/time at which this episode will become visible to registered users (without headstarts)")

    unlocks = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Episode that this episode is a possible prerequisite for")
    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that this episode is a part of")


    def get_headstarts_default():
        return list([timedelta(seconds=0),timedelta(seconds=0)])

    headstarts =  ArrayField(
        models.DurationField(),
        help_text="Headstart gained by the first, second, etc, finishing teams for the next episode",
        default= get_headstarts_default, blank=False, null = False)

    @property
    def is_locked(self):
        """ A boolean indicating whether or not the ep is locked """
        return timezone.now() < self.start_date

    @property
    def is_open(self):
        """ A boolean indicating whether or not the ep is open"""
        return timezone.now() >= self.start_date


    def __str__(self):
        return self.ep_name + " - " + self.hunt.hunt_name



class PuzzleManager(models.Manager):
    """ Manager to reorder correctly puzzles within an episode """

    def reorder(self, puz, old_number, old_episode, puz_is_new):
        """ Reorder the puzzles after a change of number/episode for puz """

        qs = self.get_queryset()
        num_puzzles = len(puz.episode.puzzle_set.all())
        ep_changed = (puz.episode.ep_number!=old_episode.ep_number)

        # If necessary, we clip the value of puzzle_number
        if puz.puzzle_number>num_puzzles:
            puz.puzzle_number = num_puzzles+1 if (ep_changed or puz_is_new) else num_puzzles
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
        unique=True,
        help_text="A 3-12 characters string that uniquely identifies the puzzle")
    answer = models.CharField(
        max_length=100,
        help_text="The answer to the puzzle, not case nor space sensitive. Can contain parentheses to show multiple options but a regex is then mandatory.")
    answer_regex = models.CharField(
        max_length=100,
        help_text="The regexp towards which the guess is checked in addition to the answer (optional, not used for demo puzzles)",
        blank=True,
        default= "")
    template = models.TextField(
        default="",
        help_text="The template string to be rendered to HTML on the puzzle page")
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
    demo_response = models.TextField(
        blank=True,
        default = "",
        help_text="For demo puzzles, this string will be displayed when the solution is found"
    )

    objects = PuzzleManager()


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
        return str(self.puzzle_number) + "-" + str(self.puzzle_id) + " " + self.puzzle_name + " (" + self.episode.ep_name + ")"

    def starting_time_for_team(self, team):
        episode = self.episode
        if team is None:
            return episode.start_date
        else:
            try:
                puz_unlock = TeamPuzzleLink.objects.get(puzzle=self, team=team)
                ep_unlock = TeamEpisodeLink.objects.get(episode=episode, team=team)
                return max(puz_unlock.time,episode.start_date-ep_unlock.headstart)
            except TeamPuzzleLink.DoesNotExist:
                return episode.start_date
            except TeamEpisodeLink.DoesNotExist:
                return episode.start_date


def puzzle_file_path(instance, filename):
    return 'puzzles/{0}/{1}'.format(instance.puzzle.id, filename)


def solution_file_path(instance, filename):
    return 'solutions/{0}/{1}'.format(instance.puzzle.id, filename)


class PuzzleFile(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    slug = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Template Slug',
        help_text="Include the URL of the file in puzzle content using $slug or ${slug}.",
    )
    url_path = models.CharField(
        max_length=50,
        verbose_name='URL Filename',
        help_text='The file path you want to appear in the URL. Can include "directories" using /',
    )
    file = models.FileField(
        upload_to=puzzle_file_path,
        help_text='The extension of the uploaded file will determine the Content-Type of the file when served',
    )

    class Meta:
        unique_together = (('puzzle', 'slug'), ('puzzle', 'url_path'))

    def __str__(self):
        return "$" + self.slug + " => " + self.url_path


class SolutionFile(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    slug = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Template Slug',
        help_text="Include the URL of the file in puzzle content using $slug or ${slug}.",
    )
    url_path = models.CharField(
        max_length=50,
        verbose_name='URL Filename',
        help_text='The file path you want to appear in the URL. Can include "directories" using /',
    )
    file = models.FileField(
        upload_to=solution_file_path,
        help_text='The extension of the uploaded file will determine the Content-Type of the file when served',
    )

    class Meta:
        unique_together = (('puzzle', 'slug'), ('puzzle', 'url_path'))

    def __str__(self):
        return "$" + self.slug + " => " + self.url_path



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
    admin_only = models.BooleanField(
        help_text="Only show it in admin panels and not to users",
        default=False)

    def __str__(self):
        return self.answer + " (" + self.regex + ") => " + self.feedback + " [" + self.puzzle.puzzle_name + "]"

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
    number_eurekas = models.IntegerField(
        verbose_name='Number required',
        help_text=('How many Eurekas are reguired to trigger the shorter time'),
        default = 1,
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

    def delay_for_team(self, team):
        """Returns how long until the hint unlocks for the given team.

        Parameters as for `unlocked_by`.
        """
        if team is None:
            return self.time
        else:
            if self.eurekas.all().count() > 0:
              teams_eurekas = team.teameurekalink_set.all()
              start_time = self.starting_time_for_team(team)
              eureka_times = []
              for eureka in self.eurekas.all():
                for team_eureka in teams_eurekas:
                  if eureka == team_eureka.eureka:
                      eureka_times.append(team_eureka.time - start_time)
              if len(eureka_times) >= self.number_eurekas:
                return min(self.time, max(eureka_times) + self.short_time)
              else:
                return self.time
            else:
                return self.time

    def starting_time_for_team(self, team):
        return self.puzzle.starting_time_for_team(team)





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



class APIToken(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return str(self.token)
