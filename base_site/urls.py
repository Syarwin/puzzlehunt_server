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
