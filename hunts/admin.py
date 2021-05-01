from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.contrib.admin.widgets import FilteredSelectMultiple
import re

from . import models
from teams.widgets import HtmlEditor


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
        models.Puzzle.objects.reorder(puz, old_number, old_episode) 

        # if self.instance.pk:
        #     # we reorder the puzzles
        #     puz = models.Puzzle.objects.get(pk=self.instance.pk)
        #     puz_number = self.cleaned_data.get('puzzle_number')
        #     episode = self.cleaned_data.get('episode')
        #     models.Puzzle.objects.move(puz, puz_number, episode) 

        #     # we save the form data and update the reverse unlocks
        #     puz = super(PuzzleAdminForm, self).save(*args, **kwargs) 
        #     puz.puzzle_set.clear()
        #     puz.puzzle_set.add(*self.cleaned_data['reverse_unlocks'])
        # else:
        #     # We backup the user-defined puzzle_number, but initially push the new puzzle at the end.
        #     kwargs["commit"] = False
        #     puz = super(PuzzleAdminForm, self).save(*args, **kwargs)
        #     puz.puzzle_number = len(puz.episode.puzzle_set.all())+1
        #     puz.save()

        #     # We then move the new puzzle to the user-defined position in the form
        #     puz_number = self.cleaned_data.get('puzzle_number')
        #     episode = self.cleaned_data.get('episode')
        #     models.Puzzle.objects.move(puz, puz_number, episode) 
        #     puz.puzzle_number = puz_number
        #     puz.save()

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

    class Meta:
        model = models.Puzzle
        fields = ('episode', 'puzzle_name', 'puzzle_number', 'puzzle_id', 'answer', 'answer_regex', 'is_meta',
                  'doesnt_count', 'puzzle_page_type', 'puzzle_file', 'resource_file',
                  'solution_file', 'extra_data', 'num_required_to_unlock', 'points_cost',
                  'points_value', 'solution_is_webpage', 'solution_resource_file')


class PuzzleAdmin(admin.ModelAdmin):
    form = PuzzleAdminForm

    list_filter = ('episode',)
    search_fields = ['puzzle_id', 'puzzle_name']
    list_display = ['combined_id', 'puzzle_name', 'episode', 'is_meta']
    list_display_links = ['combined_id', 'puzzle_name']
    ordering = ['-episode', 'puzzle_number']
    inlines = (EurekaInline,HintInline,)
    fieldsets = (
        (None, {
            'fields': ('episode', 'puzzle_name', 'answer', 'answer_regex', 'puzzle_number',
                       'puzzle_id', 'is_meta', 'doesnt_count', 'extra_data')
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


admin.site.register(models.Hunt,       HuntAdmin)
admin.site.register(models.Episode,    EpisodeAdmin)
#admin.site.register(models.Prepuzzle,  PrepuzzleAdmin)
admin.site.register(models.Puzzle,     PuzzleAdmin)
admin.site.register(models.Eureka,     EurekaAdmin)
admin.site.register(models.Hint,       HintAdmin)
#admin.site.register(models.Unlockable)