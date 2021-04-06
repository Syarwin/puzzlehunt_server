from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/hunt/', consumers.HuntWebsocket.as_asgi(), name='hunt_websocket'),
]
