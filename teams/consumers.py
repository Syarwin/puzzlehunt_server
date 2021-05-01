# Copyright (C) 2018 The Hunter2 Contributors.
#
# This file is part of Hunter2.
#
# Hunter2 is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# Hunter2 is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Hunter2.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
from collections import defaultdict
from datetime import datetime

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Guess, TeamEurekaLink
from hunts.models import Puzzle, Hunt, Hint

from . import utils



def pre_save_handler(func):
    """The purpose of this decorator is to connect signal handlers to consumer class methods.

    Before the normal signature of the signal handler, func is passed the class (as a normal classmethod) and "old",
    the instance in the database before save was called (or None). func will then be called after the current
    transaction has been successfully committed, ensuring that the instance argument is stored in the database and
    accessible via database connections in other threads, and that data is ready to be sent to clients."""
    def inner(cls, sender, instance, *args, **kwargs):
        try:
            old = type(instance).objects.get(pk=instance.pk)
        except ObjectDoesNotExist:
            old = None

        def after_commit():
            func(cls, old, sender, instance, *args, **kwargs)

        if transaction.get_autocommit():
            # in this case we want to wait until *post* save so the new object is in the db, which on_commit
            # will not do. Instead, do nothing but set an attribute on the instance to the callback, and
            # call it later in a post_save receiver.
            instance._hybrid_save_cb = after_commit
        else:  # nocover
            transaction.on_commit(after_commit)
    return classmethod(inner)

@receiver(post_save)
def hybrid_save_signal_dispatcher(sender, instance, **kwargs):
    # This checks for the attribute set by the above signal handler and calls it if it exists.
    hybrid_cb = getattr(instance, '_hybrid_save_cb', None)
    if hybrid_cb:
        # No need to pass args because this will always be a closure with the args from pre_save
        instance._hybrid_save_cb = None
        hybrid_cb()


class TeamMixin:
    channel_session_user = True
    def websocket_connect(self, message):
        # Add a team object to the scope. We can't do this in middleware because the user object
        # isn't resolved yet (I don't know what causes it to be resolved, either...) and we can't do
        # it in __init__ here because the middleware hasn't even run then, so we have no user or
        # tenant or anything!
        # This means this is a bit weirdly placed.
        try:
            hunt = get_object_or_404(Hunt, hunt_number=self.scope['url_route']['kwargs']['hunt_num'])
            self.team = hunt.team_from_user(self.scope['user'])
        except (ObjectDoesNotExist, AttributeError):
            # A user on the website will never open the websocket without getting a userprofile and team.
            self.close()
            return
        return super().websocket_connect(message)


class PuzzleWebsocket(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = False

    @classmethod
    def _puzzle_groupname(cls, puzzle, team=None):
        if team:
            return f'puzzle-{puzzle.id}.events.team-{team.id}'
        else:
            return f'puzzle-{puzzle.id}.events'

    def connect(self):
        keywords = self.scope['url_route']['kwargs']
        puzzle_id = keywords['puzzle_id']
        self.puzzle = get_object_or_404(Puzzle, puzzle_id__iexact=puzzle_id)
        self.hunt = self.puzzle.episode.hunt
        self.team = self.hunt.team_from_user(self.scope['user'])
        async_to_sync(self.channel_layer.group_add)(
            self._puzzle_groupname(self.puzzle, self.team), self.channel_name
        )
        self.setup_hint_timers()

        self.connected = True
        self.accept()

    def disconnect(self, close_code):
        super().disconnect(close_code)
        if not self.connected:
            return


    @classmethod
    def _send_message(cls, group, message):
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(group, {'type': 'send_json_msg', 'content': message})

    def send_json_msg(self, content, close=False):
        # For some reason consumer dispatch doesn't strip off the outer dictionary with 'type': 'send_json'
        # (or whatever method name) so we override and do it here. This saves us having to define a separate
        # method which just calls send_json for each type of message.
        super().send_json(content['content'])



    def setup_hint_timers(self):
        self.hint_events = {}
        hints = self.puzzle.hint_set.all()
        for hint in hints:
            self.schedule_hint(hint)

    def schedule_hint_msg(self, message):
        try:
            hint = Hint.objects.get(id=message['hint_uid'])
        except (TypeError, KeyError):
            raise ValueError('Cannot schedule a hint without either a hint instance or a dictionary with `hint_uid` key.')
        send_expired = message.get('send_expired', False)
        self.schedule_hint(hint, send_expired)

    def schedule_hint(self, hint, send_expired=False):
        try:
            self.hint_events[hint.id].cancel()
        except KeyError:
            pass

        delay = hint.delay_for_team(self.team) - (timezone.now() - hint.starting_time_for_team(self.team))
        if delay is None:
            return
        delay = delay.total_seconds()
        if not send_expired and delay < 0:
            return

        loop = sync_to_async.threadlocal.main_event_loop
        # run the hint sender function on the asyncio event loop so we don't have to bother writing scheduler stuff
        task = loop.create_task(self.send_new_hint(self.team, hint, delay))
        self.hint_events[hint.id] = task

    def cancel_scheduled_hint(self, content):
        hint = Hint.objects.get(id=content['hint_uid'])

        try:
            self.hint_events[hint.id].cancel()
            del self.hint_events[hint.id]
        except KeyError:
            pass

    @classmethod
    def send_new_hint_to_team(cls, team, hint):
        cls._send_message(cls._puzzle_groupname(hint.puzzle, team), cls._new_hint_json(hint))

    @classmethod
    def _new_hint_json(self, hint):
        return {
            'type': 'new_hint',
            'content': {
                'hint': hint.text,
                'hint_uid': hint.compact_id,
                'time': str(hint.time),
            }
        }

    async def send_new_hint(self, team, hint, delay, **kwargs):
        # We can't have a sync function (added to the event loop via call_later) because it would have to call back
        # ultimately to SyncConsumer's send method, which is wrapped in async_to_sync, which refuses to run in a thread
        # with a running asyncio event loop.
        # See https://github.com/django/asgiref/issues/56
        await asyncio.sleep(delay)

        # AsyncConsumer replaces its own base_send attribute with an async_to_sync wrapped version if the instance is (a
        # subclass of) SyncConsumer. While bizarre, the original async function is available as AsyncToSync.awaitable.
        # We also have to reproduce the functionality of JsonWebsocketConsumer and WebsocketConsumer here (they don't
        # have async versions.)
        await self.base_send.awaitable({'type': 'websocket.send', 'text': self.encode_json(self._new_hint_json(hint))})
        del self.hint_events[hint.id]



    @classmethod
    def _new_guess_json(cls, guess):
        #correct = guess.get_correct_for() is not None
        content = {
            'timestamp': str(guess.guess_time),
            'guess': guess.guess_text,
            'guess_uid': guess.id,
            'correct': False, #correct,
            'by': guess.user.username,
        }

        return content

    @classmethod
    def send_new_guess(cls, guess):
        content = cls._new_guess_json(guess)
        print(content)
        cls._send_message(cls._puzzle_groupname(guess.puzzle, guess.team), {
            'type': 'new_guess',
            'content': content
        })


    # handler: Guess.pre_save
    @pre_save_handler
    def _saved_guess(cls, old, sender, guess, raw, *args, **kwargs):
        # Do not trigger unless this was a newly created guess.
        # Note this means an admin modifying a guess will not trigger anything.
        if raw:  # nocover
            return
        if old:
            return

        """
        # required info:
        # guess, correctness, new unlocks, timestamp, whodunnit
        all_unlocks = models.Unlock.objects.filter(
            puzzle=guess.for_puzzle
        ).select_related(
            'puzzle'
        ).prefetch_related(
            'unlockanswer_set',
            'hint_set'
        )
        for u in all_unlocks:
            if any([a.validate_guess(guess) for a in u.unlockanswer_set.all()]):
                cls.send_new_unlock(guess, u)
            for hint in u.hint_set.all():
                layer = get_channel_layer()
                # It is impossible for a hint to already be unlocked if it's dependent on what we just entered,
                # so we just schedule it here rather than checking if it's unlocked and perhaps sending straight away.
                async_to_sync(layer.group_send)(cls._puzzle_groupname(guess.for_puzzle, guess.by_team), {
                    'type': 'schedule_hint_msg',
                    'hint_uid': str(hint.id)
                })
        """
        cls.send_new_guess(guess)


    @classmethod
    def _new_eureka_json(cls, eureka):
        return {
            'eureka': eureka.answer,
            'eureka_uid': eureka.id
        }

    @classmethod
    def send_new_eureka(cls, eureka, team):
        cls._send_message(cls._puzzle_groupname(eureka.puzzle, team), {
            'type': 'new_eureka',
            'content': cls._new_eureka_json(eureka)
        })


    @pre_save_handler
    def _saved_teamEurekaLink(cls, old, sender, teamEurekaLink, raw, *args, **kwargs):
        cls.send_new_eureka(teamEurekaLink.eureka, teamEurekaLink.team)


    def receive_json(self, content):
        if 'type' not in content:
            self._error('no type in message')
            return

        if content['type'] == 'guesses-plz':
            if 'from' not in content:
                self._error('required field "from" is missing')
                return
            self.send_old_guesses(content['from'])
        elif content['type'] == 'unlocks-plz':
            self.send_old_unlocks()
        elif content['type'] == 'hints-plz':
            if 'from' not in content:
                self._error('required field "from" is missing')
                return
            self.send_old_hints(content['from'])
        else:
            self._error('invalid request type')

    def _error(self, message):
        self.send_json({'type': 'error', 'content': {'error': message}})

    def send_old_guesses(self, start):
        guesses = Guess.objects.filter(puzzle=self.puzzle, team=self.team).order_by('guess_time')
        if start != 'all':
            start = datetime.fromtimestamp(int(start) // 1000, timezone.utc)
            # TODO: `start` is given by the client and is the timestamp of the most recently received guess.
            # the following could miss guesses if guesses get the same timestamp, though this is very unlikely.
            guesses = guesses.filter(guess_time__gt=start)
            # The client requested guesses from a certain point in time, i.e. it already has some.
            # Even though these are "old" they're "new" in the sense that the user will never have
            # seen them before so should trigger the same UI effect.
            msg_type = 'new_guess'
        else:
            msg_type = 'old_guess'

        for g in guesses:
            content = self._new_guess_json(g)
            self.send_json({
                'type': msg_type,
                'content': content
            })

    def send_old_hints(self, start='all'):
        hints = self.puzzle.hint_set.all()
        for hint in hints:
            delay = hint.delay_for_team(self.team) - (timezone.now() - hint.starting_time_for_team(self.team))
            delay = delay.total_seconds()
            if delay < 0:
                self.send_new_hint_to_team(self.team, hint)

    def send_old_unlocks(self):
        eurekas = self.team.eurekas.filter(puzzle=self.puzzle).order_by('teameurekalink__time')

        for u in eurekas:
            self.send_json({
                'type': 'old_eureka',
                'content': self._new_eureka_json(u)
            })


pre_save.connect(PuzzleWebsocket._saved_guess, sender=Guess)
pre_save.connect(PuzzleWebsocket._saved_teamEurekaLink, sender=TeamEurekaLink)
