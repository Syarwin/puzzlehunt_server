from django.contrib import admin
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User, Group
from django.template.defaultfilters import truncatechars
from django.contrib.sites.models import Site
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.forms import FlatpageForm
from django.db.models import Count
import re

from . import models
from .widgets import HtmlEditor


def short_team_name(teamable_object):
    return truncatechars(teamable_object.team.team_name, 50)


short_team_name.short_description = "Team name"



class PersonAdminForm(forms.ModelForm):
    def clean_teams(self):
        data = self.cleaned_data.get('teams')
        res = data.values('hunt').annotate(c=Count('hunt')).order_by('-c')
        if (res.count()>0 and res[0]['c']>1):
            raise forms.ValidationError("Several teams for the same hunt")
        return data

class PersonAdmin(admin.ModelAdmin):
    form = PersonAdminForm
    list_display = ['user_full_name', 'user_username']
    list_display_links = ['user_full_name', 'user_username']
    search_fields = ['user__email', 'user__username', 'user__first_name', 'user__last_name']
    filter_horizontal = ['teams']

    def user_full_name(self, person):
        return person.user.first_name + " " + person.user.last_name

    def user_username(self, person):
        return person.user.username

    user_full_name.short_description = "Name"
    user_username.short_description = "Username"



class GuessAdmin(admin.ModelAdmin):
    search_fields = ['guess_text','team__team_name','puzzle__puzzle_name']
    list_display = ['guess_text', short_team_name, 'guess_time']
    autocomplete_fields = ['team']
    list_filter= ('team', 'puzzle',)


class TeamAdminForm(forms.ModelForm):
    persons = forms.ModelMultipleChoiceField(
        queryset=models.Person.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('People'),
            is_stacked=False
        )
    )


    class Meta:
        model = models.Team
        fields = ['team_name', 'hunt',  'join_code', 'playtester', 'playtest_start_date',
                  'playtest_end_date', 'unlockables']

    def __init__(self, *args, **kwargs):
        super(TeamAdminForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['persons'].initial = self.instance.person_set.all()


    def clean_persons(self):
        data = self.cleaned_data.get('persons')
        for pers in data:
          if (pers.teams.filter(hunt=self.instance.hunt).exclude(pk=self.instance.pk).count() > 0): #another team within the same hunt
            raise forms.ValidationError("Person "+pers.user.username + " is in another team of the same hunt")
        return data


    def save(self, commit=True):
        team = super(TeamAdminForm, self).save(commit=False)

        if commit:
            team.save()

        if team.pk:
            team.person_set.set(self.cleaned_data['persons'])
            self.save_m2m()

        return team


class TeamAdmin(admin.ModelAdmin):
    form = TeamAdminForm
    search_fields = ['team_name']
    list_display = ['short_team_name', 'hunt', 'playtester']
    list_filter = ['hunt']
    readonly_fields = ('token', )

    def short_team_name(self, team):
        return truncatechars(team.team_name, 30) + " (" + str(team.size) + ")"

    short_team_name.short_description = "Team name"



class PuzzleSolveAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'solve_time']
    autocomplete_fields = ['team', 'guess']
    list_filter= ('team', 'puzzle',)
    search_fields = ['team__team_name','puzzle__puzzle_name']


    def solve_time(self, solve):
        return solve.guess.guess_time


class TeamPuzzleLinkAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'time']
    autocomplete_fields = ['team']
    search_fields = ['team__team_name', 'puzzle__puzzle_name']
    list_filter= ('team', 'puzzle',)


class EpisodeSolveAdmin(admin.ModelAdmin):
    list_display = ['__str__']
    autocomplete_fields = ['team']
    list_filter= ('team', 'episode',)
    search_fields = ['team__team_name','episode__ep_name']


class TeamEpisodeLinkAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'headstart']
    autocomplete_fields = ['team']
    list_filter= ('team', 'episode')
    search_fields = ['team__team_name', 'episode__ep_name']


class TeamEurekaLinkAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'time', 'puzzle_just_name']
    search_fields = ['team__team_name','eureka__puzzle__puzzle_name', 'eureka__answer']
    list_filter= ('team', 'eureka__puzzle',)

    def puzzle_just_name(self, response):
        return response.eureka.puzzle.puzzle_name

    puzzle_just_name.short_description = "Puzzle"


class UserProxyObject(User):
    class Meta:
        proxy = True
        app_label = 'teams'
        verbose_name = User._meta.verbose_name
        verbose_name_plural = "       Users"
        ordering = ['-pk']


class UserProxyAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name']
    search_fields = ['email', 'username', 'first_name', 'last_name']


class FlatPageProxyObject(FlatPage):
    class Meta:
        proxy = True
        app_label = 'teams'
        verbose_name = "info page"
        verbose_name_plural = "      Info pages"


class FlatpageProxyForm(FlatpageForm):
    class Meta:
        model = FlatPageProxyObject
        fields = '__all__'


# Define a new FlatPageAdmin
class FlatPageProxyAdmin(FlatPageAdmin):
    list_filter = []
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content')}),
        (None, {
            'classes': ('hidden',),
            'fields': ('sites',)
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': (
                'registration_required',
                'template_name',
            ),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = FlatpageProxyForm
        form = super(FlatPageAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['sites'].initial = Site.objects.get(pk=1)
        form.base_fields['content'].widget = HtmlEditor(attrs={'style': 'width:90%; height:400px;'})
        form.base_fields['url'].help_text = ("Example: '/contact-us/' translates to " +
                                             "/info/contact-us/. Make sure to have leading and " +
                                             "trailing slashes.")
        return form


admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(Site)
admin.site.unregister(FlatPage)

admin.site.register(models.Person,         PersonAdmin)
admin.site.register(models.Guess,          GuessAdmin)
admin.site.register(models.Team,           TeamAdmin)
admin.site.register(models.PuzzleSolve,    PuzzleSolveAdmin)
admin.site.register(models.TeamPuzzleLink, TeamPuzzleLinkAdmin)
admin.site.register(models.EpisodeSolve,   EpisodeSolveAdmin)
admin.site.register(models.TeamEpisodeLink,TeamEpisodeLinkAdmin)
admin.site.register(models.TeamEurekaLink, TeamEurekaLinkAdmin)
admin.site.register(UserProxyObject,       UserProxyAdmin)
admin.site.register(FlatPageProxyObject,   FlatPageProxyAdmin)
