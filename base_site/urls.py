# Copyright (C) 2018 The MindbreakersServer Contributors.
#
# This file is part of MindbreakersServer.
#
# MindbreakersServer is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# MindbreakersServer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Hunter2.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import include, url
from django.urls import path, reverse_lazy, include
from django.conf import settings
from baton.autodiscover import admin
from django.contrib.auth import views as base_auth_views
from django.views.generic.base import RedirectView
from django.contrib.flatpages import views as flatpage_views
from . import views


urlpatterns = [
	# Admin redirections/views
    url(r'^admin/login/$', RedirectView.as_view(url=reverse_lazy(settings.LOGIN_URL),
                                                query_string=True)),
    path('admin/', admin.site.urls),
    path('baton/', include('baton.urls')),
    url(r'^$', views.index, name='index'),
]
