"""puzzlehunt_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.urls import path
from django.contrib.auth import views as base_auth_views
from django.views.generic.base import RedirectView
from django.contrib.flatpages import views as flatpage_views
from . import views

urlpatterns = [
     # Info Pages
    url(r'^$', views.info.index, name='index'),
    #url(r'^previous-hunts/$', views.info.previous_hunts, name='previous_hunts'),
    path('info/', include('django.contrib.flatpages.urls')),
    path('info-and-rules/', flatpage_views.flatpage, {'url': '/hunt-info/'}, name='current_hunt_info'),

    # Hunt Pages
    url(r'^hunt/current/$', views.hunt.current_hunt, name='current_hunt'),
    url(r'^hunt/(?P<hunt_num>[0-9]+)/$', views.hunt.HuntIndex.as_view(), name='hunt'),
    url(r'^puzzle/(?P<puzzle_id>[0-9a-zA-Z]{3,12})/$', views.hunt.PuzzleView.as_view(), name='puzzle'),
    #url(r'^hunt/(?P<hunt_num>[0-9]+)/prepuzzle/$', hunt_views.hunt_prepuzzle, name='hunt_prepuzzle'),
    #url(r'^prepuzzle/(?P<prepuzzle_num>[0-9]+)/$', hunt_views.prepuzzle, name='prepuzzle'),
    #url(r'^objects/$', hunt_views.unlockables, name='unlockables'),
    url(r'^protected/(?P<file_path>.+)$', views.hunt.protected_static, name='protected_static'),
    url(r'^leaderboard/$', views.hunt.leaderboard, name='leaderboard'),
]
