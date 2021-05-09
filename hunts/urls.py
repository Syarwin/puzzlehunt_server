"""server URL Configuration

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


puzzlepatterns = [
    path('', views.hunt.PuzzleView.as_view(), name='puzzle'),
#    path('an', views.player.Answer.as_view(), name='answer'),
#    path('cb', views.player.Callback.as_view(), name='callback'),
    path('media/<path:file_path>', views.hunt.PuzzleFile.as_view(), name='puzzle_file'),
#    path('soln', views.player.SolutionContent.as_view(), name='solution_content'),
#    path('soln/media/<path:file_path>', views.player.SolutionFile.as_view(), name='solution_file'),
]

urlpatterns = [
     # Info Pages
    path('info/', include('django.contrib.flatpages.urls')),
    path('info-and-rules/', flatpage_views.flatpage, {'url': '/hunt-info/'}, name='current_hunt_info'),

    # Hunt Pages
    url(r'^hunt/current/$', views.hunt.current_hunt, name='current_hunt'),
    url(r'^hunt/(?P<hunt_num>[0-9]+)/$', views.hunt.HuntIndex.as_view(), name='hunt'),
    url(r'^puzzle/(?P<puzzle_id>[0-9a-zA-Z]{3,12})/', include(puzzlepatterns)),
    #url(r'^objects/$', hunt_views.unlockables, name='unlockables'),
    url(r'^leaderboard/$', views.hunt.leaderboard, name='leaderboard'),

    # Staff pages
    url(r'^staff/$', views.staff.index, name='staffindex'),
    url(r'^staff/', include([
        url(r'^queue/$', views.staff.queue, name='queue'),
        url(r'^progress/$', views.staff.progress, name='progress'),
        url(r'^overview/$', views.staff.overview, name='overview'),
        url(r'^charts/$', views.staff.charts, name='charts'),
        url(r'^control/$', views.staff.control, name='control'),
        url(r'^teams/$', RedirectView.as_view(url='/admin/teams/team/', permanent=False)),
        url(r'^puzzles/$', RedirectView.as_view(url='/admin/hunts/puzzle/', permanent=False)),
#        url(r'^emails/$', views.staff.emails, name='emails'),
        url(r'^management/$', views.staff.hunt_management, name='hunt_management'),
        url(r'^info/$', views.staff.hunt_info, name='hunt_info'),
        url(r'^lookup/$', views.staff.lookup, name='lookup'),
        url(r'^puzzle_dag/$', views.staff.puzzle_dag, name='puzzle_dag'),
    ])),

    # Stats pages
    url(r'^stats/$', views.stats.stats, name='statsi'),
    url(r'^stats/', include([
        url(r'^stats/$', views.stats.stats, name='stats'),
        url(r'^teams/$', views.stats.teams, name='teams'),
        url(r'^team/$', views.stats.team, name='team'),
        url(r'^puzzles/$', views.stats.puzzles, name='puzzles'),
        url(r'^puzzle/$', views.stats.puzzle, name='puzzle'),
        url(r'^charts/$', views.stats.charts, name='charts_stats'),
    ])),
]
