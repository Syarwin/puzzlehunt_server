from django.urls import path, re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/hunt/(?P<hunt_num>[0-9]+)/puzzle/(?P<puzzle_id>[0-9a-zA-Z]{3,12})/$", consumers.PuzzleWebsocket.as_asgi(), name='puzzle_websocket'),
]
