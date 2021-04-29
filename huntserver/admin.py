from django.contrib import admin
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple
from huntserver.widgets import HtmlEditor
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe
from django.template.defaultfilters import truncatechars
from django.contrib.sites.models import Site
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.forms import FlatpageForm
import re

# Register your models here.
from . import models


def short_team_name(teamable_object):
    return truncatechars(teamable_object.team.team_name, 50)


short_team_name.short_description = "Team name"

class PersonAdmin(admin.ModelAdmin):
    list_display = ['user_full_name', 'user_username']
    search_fields = ['user__email', 'user__username', 'user__first_name', 'user__last_name']
    filter_horizontal = ['teams']

    def user_full_name(self, person):
        return person.user.first_name + " " + person.user.last_name

    def user_username(self, person):
        return person.user.username

    user_full_name.short_description = "Name"
    user_username.short_description = "Username"



class HuntAdminForm(forms.ModelForm):
    model = models.Hunt

    class Meta:
        widgets = {
            'template': HtmlEditor(attrs={'style': 'width: 90%; height: 400px;'}),
        }


class HuntAdmin(admin.ModelAdmin):
    form = HuntAdminForm
    fieldsets = (
        ('Basic Info', {'fields': ('hunt_name', 'hunt_number', 'team_size',
                        ('start_date', 'display_start_date'), ('end_date', 'display_end_date'),
                        'is_current_hunt')}),
        ('Hunt Behaviour', {'fields': ('points_per_minute',)}),
        ('Resources/Template', {'fields': ('resource_file', 'extra_data', 'template')}),
    )

    list_display = ['hunt_name', 'team_size', 'start_date', 'is_current_hunt']


class EpisodeAdminForm(forms.ModelForm):
    class Meta:
        model = models.Episode
        fields = ['hunt', 'ep_name', 'ep_number', 'start_date']

class EpisodeAdmin(admin.ModelAdmin):
    form = EpisodeAdminForm
    list_display = ['ep_name', 'start_date']



class PrepuzzleAdminForm(forms.ModelForm):
    class Meta:
        model = models.Prepuzzle
        fields = ['puzzle_name', 'released', 'hunt', 'answer', 'resource_file', 'template',
                  'response_string']
        widgets = {
            'template': HtmlEditor(attrs={'style': 'width: 90%; height: 400px;'}),
        }


class PrepuzzleAdmin(admin.ModelAdmin):
    form = PrepuzzleAdminForm
    list_display = ['puzzle_name', 'hunt', 'released']
    readonly_fields = ('puzzle_url',)

    # Needed to add request to modelAdmin
    def get_queryset(self, request):
        qs = super(PrepuzzleAdmin, self).get_queryset(request)
        self.request = request
        return qs

    def puzzle_url(self, obj):
        puzzle_url_str = "http://" + self.request.get_host() + "/prepuzzle/" + str(obj.pk) + "/"
        html = puzzle_url_str + '<button class="clipboard-btn" data-clipboard-text="' + puzzle_url_str + '" type="button">Copy Puzzle URL</button>'
        return mark_safe(html)

    puzzle_url.short_description = 'Puzzle URL: (Not editable)'


class UnlockInline(admin.TabularInline):
    model = models.Puzzle.unlocks.through
    extra = 2
    fk_name = 'to_puzzle'
    verbose_name = "Puzzle that counts towards unlocking this puzzle"
    verbose_name_plural = "Puzzles that count towards this puzzle"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "from_puzzle":
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                puzzle = models.Puzzle.objects.get(id=parent_obj_id)
                query = models.Puzzle.objects.filter(hunt=puzzle.episode.hunt)
                kwargs["queryset"] = query.order_by('puzzle_id')
            except IndexError:
                pass
        return super(UnlockInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class EurekaInline(admin.TabularInline):
    model = models.Eureka
    extra = 1

class HintInline(admin.TabularInline):
    model = models.Hint
    extra = 1


class PuzzleAdminForm(forms.ModelForm):
    reverse_unlocks = forms.ModelMultipleChoiceField(
        models.Puzzle.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Puzzle', False),
        required=False,
        label="Puzzles that count towards this puzzle"
    )

    def __init__(self, *args, **kwargs):
        super(PuzzleAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['reverse_unlocks'] = self.instance.puzzle_set.values_list('pk', flat=True)
            choices = self.instance.episode.puzzle_set.values_list('pk', 'puzzle_name')
            self.fields['reverse_unlocks'].choices = choices

    def save(self, *args, **kwargs):
        instance = super(PuzzleAdminForm, self).save(*args, **kwargs)
        if instance.pk:
            instance.puzzle_set.clear()
            instance.puzzle_set.add(*self.cleaned_data['reverse_unlocks'])
        return instance

    def clean_answer(self):
        data = self.cleaned_data.get('answer')
        if(re.fullmatch(r"[a-zA-Z0-9 \(\)]+", data.upper()) is None):
            raise forms.ValidationError("Answer must only contain the characters A-Z- -(-) and digits.")
        return data
        
    def clean_answer_regex(self):
        data = self.cleaned_data.get('answer_regex')
        if(re.fullmatch(r".* .*", data)):
            raise forms.ValidationError("Answer regex must not contain spaces.")
        if (data == "" and re.fullmatch(r".*[\(\)].*", self.cleaned_data.get('answer'))):
            raise forms.ValidationError("Answer regex is empty but Answer contains non-alphanumerical character: the puzzle has no answer.")
        return data

    class Meta:
        model = models.Puzzle
        fields = ('episode', 'puzzle_name', 'puzzle_number', 'puzzle_id', 'answer', 'answer_regex', 'is_meta',
                  'doesnt_count', 'puzzle_page_type', 'puzzle_file', 'resource_file',
                  'solution_file', 'extra_data', 'num_required_to_unlock', 'unlock_type',
                  'points_cost', 'points_value', 'solution_is_webpage', 'solution_resource_file')


class PuzzleAdmin(admin.ModelAdmin):
    class Media:
        js = ("huntserver/admin_change_puzzle.js",)

    form = PuzzleAdminForm

    list_filter = ('episode',)
    search_fields = ['puzzle_id', 'puzzle_name']
    list_display = ['combined_id', 'puzzle_name', 'episode', 'is_meta']
    list_display_links = ['combined_id', 'puzzle_name']
    ordering = ['-episode', 'puzzle_number']
    inlines = (EurekaInline,HintInline,)
    radio_fields = {"unlock_type": admin.VERTICAL}
    fieldsets = (
        (None, {
            'fields': ('episode', 'puzzle_name', 'answer', 'answer_regex', 'puzzle_number', 'puzzle_id', 'is_meta',
                       'doesnt_count', 'extra_data', 'unlock_type')
        }),
        ('Resources', {
            'classes': ('formset_border', 'resources'),
            'fields': ('puzzle_page_type', 'puzzle_file', 'resource_file', 'template',
                   'solution_is_webpage', 'solution_file', 'solution_resource_file',)
        }),
        ('Solve Unlocking', {
            'classes': ('formset_border', 'solve_unlocking'),
            'fields': ('reverse_unlocks', 'num_required_to_unlock')
        }),
        ('Points Unlocking', {
            'classes': ('formset_border', 'points_unlocking'),
            'fields': ('points_cost', 'points_value')
        }),
    )

    def combined_id(self, puzzle):
        return str(puzzle.puzzle_number) + "-" + puzzle.puzzle_id

    combined_id.short_description = "ID"


class EurekaAdmin(admin.ModelAdmin):
    list_display = ['puzzle_just_name', 'answer', 'regex', 'feedback']
    list_display_links = ['answer', 'regex', 'feedback']
    search_fields = ['answer', 'regex', 'feedback']
    ordering = ['-puzzle']

    def puzzle_just_name(self, response):
        return response.puzzle.puzzle_name

    puzzle_just_name.short_description = "Puzzle"

class HintAdmin(admin.ModelAdmin):
    list_display = ['puzzle_just_name', 'text', 'time', 'short_time']
    list_display_links = ['text']
    search_fields = ['text']
    ordering = ['-puzzle']

    def puzzle_just_name(self, response):
        return response.puzzle.puzzle_name

    puzzle_just_name.short_description = "Puzzle"


class PuzzleSolveAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'solve_time']
    autocomplete_fields = ['team', 'guess']

    def solve_time(self, solve):
        return solve.guess.guess_time


class EurekaUnlockAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'time']


class GuessAdmin(admin.ModelAdmin):
    search_fields = ['guess_text']
    list_display = ['guess_text', short_team_name, 'guess_time']
    autocomplete_fields = ['team']


class TeamAdminForm(forms.ModelForm):
    persons = forms.ModelMultipleChoiceField(
        queryset=models.Person.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('People'),
            is_stacked=False
        )
    )

    num_unlock_points = forms.IntegerField(disabled=True)

    class Meta:
        model = models.Team
        fields = ['team_name', 'hunt',  'join_code', 'playtester', 'playtest_start_date',
                  'playtest_end_date', 'num_unlock_points', 'unlockables']

    def __init__(self, *args, **kwargs):
        super(TeamAdminForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['persons'].initial = self.instance.person_set.all()

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

    def short_team_name(self, team):
        return truncatechars(team.team_name, 30) + " (" + str(team.size) + ")"

    short_team_name.short_description = "Team name"


class PuzzleUnlockAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'time']
    autocomplete_fields = ['team']


class UserProxyObject(User):
    class Meta:
        proxy = True
        app_label = 'huntserver'
        verbose_name = User._meta.verbose_name
        verbose_name_plural = User._meta.verbose_name_plural
        ordering = ['-pk']


class UserProxyAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name']
    search_fields = ['email', 'username', 'first_name', 'last_name']


class FlatPageProxyObject(FlatPage):
    class Meta:
        proxy = True
        app_label = 'huntserver'
        verbose_name = "info page"
        verbose_name_plural = "info pages"


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

admin.site.register(models.Person,     PersonAdmin)
admin.site.register(models.Hunt,       HuntAdmin)
admin.site.register(models.Episode,    EpisodeAdmin)
#admin.site.register(models.Prepuzzle,  PrepuzzleAdmin)
admin.site.register(models.Puzzle,     PuzzleAdmin)
admin.site.register(models.Eureka,     EurekaAdmin)
admin.site.register(models.Hint,       HintAdmin)
admin.site.register(models.PuzzleSolve,PuzzleSolveAdmin)
admin.site.register(models.Guess, GuessAdmin)
admin.site.register(models.Team,       TeamAdmin)
#admin.site.register(models.Unlockable)
admin.site.register(models.PuzzleUnlock, PuzzleUnlockAdmin)
admin.site.register(models.EurekaUnlock, EurekaUnlockAdmin)
admin.site.register(UserProxyObject,   UserProxyAdmin)
admin.site.register(FlatPageProxyObject, FlatPageProxyAdmin)
