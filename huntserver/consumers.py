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
from .models import Puzzle, Hunt

from . import models, utils


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


class PuzzleWebsocket(TeamMixin, JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = False

    @classmethod
    def _puzzle_groupname(cls, puzzle, team=None):
        hunt = puzzle.hunt
        if team:
            return f'hunt-{hunt.id}.puzzle-{puzzle.id}.events.team-{team.id}'
        else:
            return f'hunt-{hunt.id}.puzzle-{puzzle.id}.events'

    def connect(self):
        keywords = self.scope['url_route']['kwargs']
        puzzle_id = keywords['puzzle_id']
        self.puzzle = get_object_or_404(Puzzle, puzzle_id__iexact=puzzle_id)
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
            hint = models.Hint.objects.get(id=message['hint_uid'])
        except (TypeError, KeyError):
            raise ValueError('Cannot schedule a hint without either a hint instance or a dictionary with `hint_uid` key.')
        send_expired = message.get('send_expired', False)
        self.schedule_hint(hint, send_expired)

    def schedule_hint(self, hint, send_expired=False):
        try:
            self.hint_events[hint.id].cancel()
        except KeyError:
            pass

        delay = hint.delay_for_team(self.team)
        print("Test", delay)
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
        hint = models.Hint.objects.get(id=content['hint_uid'])

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
