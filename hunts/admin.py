from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.html import format_html

import re

from . import models
from teams.widgets import HtmlEditor
from . import widgets


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
                        'is_current_hunt', 'eureka_feedback')}),
    )

    list_display = ['hunt_name', 'team_size', 'start_date', 'is_current_hunt']



class EpisodeAdminForm(forms.ModelForm):
    class Meta:
        model = models.Episode
        fields = ['hunt', 'ep_name', 'ep_number', 'unlocks', 'start_date']

class EpisodeAdmin(admin.ModelAdmin):
    form = EpisodeAdminForm
    list_display = ['ep_name', 'start_date', 'hunt_just_name', 'unlocks']
    
    #remove self-reference to episode. TODO: small bug when creating an episode, cannot choose to unlock the last one opened
    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.object_id = object_id
        return super(EpisodeAdmin, self).change_view(request, object_id, form_url, extra_context=extra_context)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "unlocks":
            kwargs['queryset'] = models.Episode.objects.exclude(pk=self.object_id)
        return super(EpisodeAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
    
    def hunt_just_name(self, response):
        return response.hunt.hunt_name

    hunt_just_name.short_description = "Hunt"


class PrepuzzleAdminForm(forms.ModelForm):
    class Meta:
        model = models.Prepuzzle
        fields = ['puzzle_name', 'released', 'hunt', 'answer', 'template',
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
    extra = 3

class HintInline(admin.TabularInline):
    model = models.Hint
    extra = 5

    #remove eurekas belonging to other puzzles
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "eurekas":
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                puzzle = models.Puzzle.objects.get(id=parent_obj_id)
                query = models.Eureka.objects.filter(puzzle=puzzle)
                kwargs["queryset"] = query
            except IndexError:
                pass
            except KeyError:
                pass
        return super(HintInline, self).formfield_for_manytomany(db_field, request, **kwargs)

class PuzzleFileInline(admin.TabularInline):
    model = models.PuzzleFile
    extra = 2

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'file':
            kwargs['widget'] = widgets.CustomAdminFileWidget()
            return db_field.formfield(**kwargs)
        return super(PuzzleFileInline,self).formfield_for_dbfield(db_field,request,**kwargs)


class SolutionFileInline(admin.TabularInline):
    model = models.SolutionFile
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
            choices = self.instance.episode.puzzle_set.exclude(pk=self.instance.pk).values_list('pk', 'puzzle_name')
            self.fields['reverse_unlocks'].choices = choices

    def save(self, *args, **kwargs):
        if self.instance.pk:
            old_puz = models.Puzzle.objects.get(pk=self.instance.pk)
            old_episode = old_puz.episode
            old_number = old_puz.puzzle_number
        else:
            # If the puzzle is new, we force reordering by assuming that the (virtual) old
            # puzzle is at the end
            old_episode = self.cleaned_data.get('episode')
            old_number = len(self.instance.episode.puzzle_set.all())+1

        puz = super(PuzzleAdminForm, self).save(*args, **kwargs)
        models.Puzzle.objects.reorder(puz, old_number, old_episode, not self.instance.pk)
        if puz.pk:
            puz.puzzle_set.clear()
            puz.puzzle_set.add(*self.cleaned_data['reverse_unlocks'])
        return puz

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

    # warn if puzzle cannot be unlocked by users
    def clean(self):
        if ('warn_possible_duplicate' not in self.data): 
          num = self.cleaned_data.get('num_required_to_unlock')
          lis = self.cleaned_data.get('reverse_unlocks')
          if num > len(lis):
              self.add_error('num_required_to_unlock', format_html(
                  'Puzzle cannot be unlocked by users (too many prerequisites required).'
                  ' To add the new entry anyway, please save again.'
                  '<input type="hidden" id="warn-possible-duplicate"' # inject hidden input with error msg itself
                  'name="warn_possible_duplicate" value="0"/>'        # so it's returned in form `data` on second save
              ))
          if num == 0 and len(lis)>0:
              self.add_error('num_required_to_unlock', format_html(
                  'Puzzle have prerequisites which are not used: it will be unlocked by default.'
                  ' To add the new entry anyway, please save again.'
                  '<input type="hidden" id="warn-possible-duplicate"' # inject hidden input with error msg itself
                  'name="warn_possible_duplicate" value="0"/>'        # so it's returned in form `data` on second save
              ))

    class Meta:
        model = models.Puzzle
        fields = ('episode', 'puzzle_name', 'puzzle_number', 'puzzle_id', 'answer', 'answer_regex',
                  'num_required_to_unlock',)


class PuzzleAdmin(admin.ModelAdmin):
    form = PuzzleAdminForm

    list_filter = ('episode',)
    search_fields = ['puzzle_id', 'puzzle_name']
    list_display = ['combined_id', 'puzzle_name', 'episode']
    list_display_links = ['combined_id', 'puzzle_name']
    ordering = ['episode', 'puzzle_number']
    inlines = (PuzzleFileInline,SolutionFileInline,EurekaInline,HintInline,)
    fieldsets = (
        (None, {
            'fields': ('episode', 'puzzle_name', 'answer', 'answer_regex', 'puzzle_number',
                       'puzzle_id', 'extra_data')
        }),
        ('Resources', {
            'classes': ('formset_border', 'resources'),
            'fields': ('template',)
        }),
        ('Solve Unlocking', {
            'classes': ('formset_border', 'solve_unlocking'),
            'fields': ('reverse_unlocks', 'num_required_to_unlock')
        })
    )

    def combined_id(self, puzzle):
        return str(puzzle.puzzle_number) + "-" + puzzle.puzzle_id

    combined_id.short_description = "ID"


class EurekaAdmin(admin.ModelAdmin):
    list_display = ['puzzle_just_name', 'answer', 'regex', 'feedback']
    list_display_links = ['answer', 'regex', 'feedback']
    search_fields = ['answer', 'regex', 'feedback','puzzle__puzzle_name']
    ordering = ['-puzzle']
    list_filter = ['puzzle']

    def puzzle_just_name(self, response):
        return response.puzzle.puzzle_name

    puzzle_just_name.short_description = "Puzzle"

class HintAdmin(admin.ModelAdmin):
    list_display = ['puzzle_just_name', 'text', 'time', 'number_eurekas', 'short_time']
    list_display_links = ['text']
    search_fields = ['text']
    ordering = ['-puzzle']
    list_filter =  ['puzzle']

    def puzzle_just_name(self, response):
        return response.puzzle.puzzle_name

    puzzle_just_name.short_description = "Puzzle"


admin.site.register(models.Hunt,       HuntAdmin)
admin.site.register(models.Episode,    EpisodeAdmin)
admin.site.register(models.Prepuzzle,  PrepuzzleAdmin)
admin.site.register(models.Puzzle,     PuzzleAdmin)
admin.site.register(models.Eureka,     EurekaAdmin)
admin.site.register(models.Hint,       HintAdmin)
#admin.site.register(models.Unlockable)
