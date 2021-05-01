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
    # Auth and Accounts
    url(r'^signup/$', views.auth.SignUp.as_view(), name='signup'),
    url(r'^login/$', views.auth.account_login, name='login'),
    url(r'^logout/$', views.auth.account_logout, name='logout'),
    url(r'^registration/$', views.auth.Registration.as_view(), name='registration'),
    url(r'^manage-team/$', views.auth.ManageTeam.as_view(), name='manage-team'),
    url(r'^profile/$', views.auth.profile, name='profile'),

    # Staff pages
    url(r'^staff/', include([
        url(r'^queue/$', views.staff.queue, name='queue'),
        url(r'^progress/$', views.staff.progress, name='progress'),
        url(r'^charts/$', views.staff.charts, name='charts'),
        url(r'^control/$', views.staff.control, name='control'),
        url(r'^teams/$', RedirectView.as_view(url='/admin/teams/team/', permanent=False)),
        url(r'^puzzles/$', RedirectView.as_view(url='/admin/hunts/puzzle/', permanent=False)),
        url(r'^emails/$', views.staff.emails, name='emails'),
        url(r'^management/$', views.staff.hunt_management, name='hunt_management'),
        url(r'^info/$', views.staff.hunt_info, name='hunt_info'),
        url(r'^lookup/$', views.staff.lookup, name='lookup'),
    ])),
]
