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
from django.contrib.auth import views as base_auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from base_site.urls import urlpatterns as base_patterns
from hunts.urls import urlpatterns as hunts_patterns
from teams.urls import urlpatterns as teams_patterns

urlpatterns = [
    # User auth/password reset
    url(r'^accounts/logout/$', base_auth_views.LogoutView.as_view(),
        name='logout', kwargs={'next_page': '/'}),
    url(r'^accounts/login/$', base_auth_views.LoginView.as_view()),
    url(r'^password_reset/$', base_auth_views.PasswordResetView.as_view(), name='password_reset'),
    url(r'^password_reset/done/$', base_auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        base_auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url(r'^reset/done/$', base_auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),
] \
    + staticfiles_urlpatterns() \
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
    + base_patterns \
    + hunts_patterns \
    + teams_patterns


# Use silk if enabled
if 'silk' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^silk/', include('silk.urls', namespace='silk')))
