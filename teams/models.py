from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.dateformat import DateFormat
from dateutil import tz
from django.conf import settings
from datetime import timedelta
from enum import Enum

import os
import re
import zipfile
import shutil
import logging
logger = logging.getLogger(__name__)

time_zone = tz.gettz(settings.TIME_ZONE)

class TeamManager(models.Manager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (models.Q(team_name__icontains=query) |
                         models.Q(location__icontains=query))
            qs = qs.filter(or_lookup).distinct()
        return qs


class Team(models.Model):
    """ A class representing a team within a hunt """
    class Meta:
        verbose_name_plural = "       Teams"

    team_name = models.CharField(
        max_length=200,
        help_text="The team name as it will be shown to hunt participants")
    location = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        help_text="The country the members of the team are from")
    solved = models.ManyToManyField(
        "hunts.Puzzle",
        blank=True,
        related_name='solved_for',
        through="PuzzleSolve",
        help_text="The puzzles the team has solved")
    unlocked = models.ManyToManyField(
        "hunts.Puzzle",
        blank=True,
        related_name='unlocked_for',
        through="TeamPuzzleLink",
        help_text="The puzzles the team has unlocked")
    eurekas = models.ManyToManyField(
        "hunts.Eureka",
        blank=True,
        related_name='eurekas_for',
        through="TeamEurekaLink",
        help_text="The eurekas the team has unlocked")
    unlockables = models.ManyToManyField(
        "hunts.Unlockable",
        blank=True,
        help_text="The unlockables the team has earned")
    hunt = models.ForeignKey(
        "hunts.Hunt",
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
        puzzles = [puzzle for episode in self.hunt.episode_set.all() for puzzle in episode.puzzle_set.all()]
        numbers = []

        numbers = [puz.puzzle_number for puz in puzzles]
        # make an array for how many points a team has towards unlocking each puzzle
        mapping = [0 for i in range(max(numbers) + 1)]

        # go through each solved puzzle and add to the list for each puzzle it unlocks
        for puz in self.solved.all():
            for num in puz.unlocks.values_list('puzzle_number', flat=True):
                mapping[num] += 1

        # See if we can unlock any given puzzle
        unlocked_numbers = [puz.puzzle_number for puz in self.unlocked.all()]
        for puz in puzzles:
            if (puz.puzzle_number in unlocked_numbers):
                continue
            if(puz.num_required_to_unlock <= mapping[puz.puzzle_number]):
                logger.info("Team %s unlocked puzzle %s with solves" % (str(self.team_name),
                            str(puz.puzzle_id)))
                PuzzleUnlock.objects.create(team=self, puzzle=puz, time=timezone.now())

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
    class Meta:
        verbose_name_plural = "      Persons"

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
        verbose_name_plural = '   Guesses'

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
        "hunts.Puzzle",
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
        """ A boolean indicating if the guess given is exactly correct (matches either the
        answer or the non-empty regex). Spaces do not matter so are removed. """
        noSpace = self.guess_text.upper().replace(" ","")
        return ( noSpace == self.puzzle.answer.upper().replace(" ","") or 
                 (self.puzzle.answer_regex!="" and re.fullmatch(self.puzzle.answer_regex, noSpace, re.IGNORECASE)) )

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
                if(re.fullmatch(resp.regex.replace(" ",""), noSpace, re.IGNORECASE)):
                    if(resp not in self.team.eurekas.all()):
                        TeamEurekaLink.objects.create(team=self.team, eureka=resp, time=timezone.now())
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
    class Meta:
        verbose_name_plural = "  Puzzles solved by teams"
        unique_together = ('puzzle', 'team',)

    puzzle = models.ForeignKey(
        "hunts.Puzzle",
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



class TeamPuzzleLink(models.Model):
    """ A class that links a team and a puzzle to indicate that the team has unlocked the puzzle """
    class Meta:
        unique_together = ('puzzle', 'team',)
        verbose_name_plural = " Puzzles unlocked by teams"

    puzzle = models.ForeignKey(
        "hunts.Puzzle",
        on_delete=models.CASCADE,
        help_text="The puzzle that this is an unlock for")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that this unlocked puzzle is for")
    time = models.DateTimeField(
        help_text="The time this puzzle was unlocked for this team")
    

    def serialize_for_ajax(self):
        """ Serializes the puzzle, team, and status fields for ajax transmission """
        message = dict()
        message['puzzle'] = self.puzzle.serialize_for_ajax()
        message['team_pk'] = self.team.pk
        message['status_type'] = "unlock"
        return message

    def __str__(self):
        return self.team.short_name + ": " + self.puzzle.puzzle_name





class TeamEurekaLink(models.Model):
    """ A class that links a team and a eureka to indicate that the team has unlocked the eureka """
    class Meta:
        unique_together = ('eureka', 'team',)
        verbose_name_plural = "Eurekas unlocked by teams"

    eureka = models.ForeignKey(
        "hunts.Eureka",
        on_delete=models.CASCADE,
        help_text="The eureka unlocked")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that this unlocked puzzle is for")
    time = models.DateTimeField(
        help_text="The time this eureka was unlocked for this team")

    
    def serialize_for_ajax(self):
        """ Serializes the puzzle, team, and status fields for ajax transmission """
        message = dict()
        message['eureka'] = self.eureka.pk
        message['team_pk'] = self.team.pk
        message['status_type'] = "unlock"
        return message

    def __str__(self):
        return self.team.short_name + ": " + self.eureka.answer