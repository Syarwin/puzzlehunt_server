# Generated by Django 3.1.7 on 2021-04-30 19:20

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import hunts.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Episode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ep_name', models.CharField(help_text='The name of the episode as the public will see it', max_length=200)),
                ('ep_number', models.IntegerField(help_text='A number used internally for hunt sorting, must be unique', unique=True)),
                ('start_date', models.DateTimeField(help_text='The date/time at which a hunt will become visible to registered users')),
            ],
            options={
                'verbose_name_plural': '   Episodes',
            },
        ),
        migrations.CreateModel(
            name='Eureka',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('regex', models.CharField(help_text="The python-style regex that will be checked against the user's response", max_length=400)),
                ('answer', models.CharField(help_text='The text to use in the guess response if the regex matched', max_length=400)),
                ('feedback', models.CharField(blank=True, help_text='The feedback message sent when this eureka is found - if blank, use the default feedback of the hunt', max_length=255)),
            ],
            options={
                'verbose_name_plural': ' Eurekas',
            },
        ),
        migrations.CreateModel(
            name='Hint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(help_text='The text to display', max_length=400)),
                ('time', models.DurationField(help_text='Time after anyone on the team first loads the puzzle', validators=[django.core.validators.MinValueValidator(datetime.timedelta(0))], verbose_name='Delay')),
                ('short_time', models.DurationField(help_text='Time after all the associated Eurekas were found', validators=[django.core.validators.MinValueValidator(datetime.timedelta(0))], verbose_name='Shorter Delay')),
            ],
            options={
                'verbose_name_plural': 'Hints',
            },
        ),
        migrations.CreateModel(
            name='Hunt',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hunt_name', models.CharField(help_text='The name of the hunt as the public will see it', max_length=200)),
                ('hunt_number', models.IntegerField(help_text='A number used internally for hunt sorting, must be unique', unique=True)),
                ('team_size', models.IntegerField()),
                ('start_date', models.DateTimeField(help_text='The date/time at which a hunt will become visible to registered users')),
                ('end_date', models.DateTimeField(help_text='The date/time at which a hunt will be archived and available to the public')),
                ('display_start_date', models.DateTimeField(help_text='The start date/time displayed to users')),
                ('display_end_date', models.DateTimeField(help_text='The end date/time displayed to users')),
                ('resource_file', models.FileField(blank=True, help_text='Hunt resources, MUST BE A ZIP FILE.', storage=hunts.models.PuzzleOverwriteStorage(), upload_to=hunts.models.get_hunt_file_path)),
                ('is_current_hunt', models.BooleanField(default=False)),
                ('extra_data', models.CharField(blank=True, help_text='A misc. field for any extra data to be stored with the hunt.', max_length=200)),
                ('template', models.TextField(default='', help_text='The template string to be rendered to HTML on the hunt page')),
                ('points_per_minute', models.IntegerField(default=0, help_text='The number of points granted per minute during the hunt')),
                ('eureka_feedback', models.CharField(blank=True, help_text='The default feedback message sent when an eureka is found', max_length=255)),
            ],
            options={
                'verbose_name_plural': '    Hunts',
            },
        ),
        migrations.CreateModel(
            name='HuntAssetFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(storage=hunts.models.OverwriteStorage(), upload_to='hunt/assets/')),
            ],
        ),
        migrations.CreateModel(
            name='Puzzle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puzzle_name', models.CharField(help_text='The name of the puzzle as it will be seen by hunt participants', max_length=200)),
                ('puzzle_number', models.IntegerField(help_text='The number of the puzzle within the episode, for sorting purposes (must be unique within the episode, and not too large)')),
                ('puzzle_id', models.CharField(help_text='A 3-12 character hex string that uniquely identifies the puzzle', max_length=12, unique=True)),
                ('answer', models.CharField(help_text='The answer to the puzzle, not case nor space sensitive. Can contain parentheses to show multiple options but a regex is then mandatory.', max_length=100)),
                ('answer_regex', models.CharField(blank=True, default='', help_text='The regexp towards which the guess is checked in addition to the answer (optional)', max_length=100)),
                ('is_meta', models.BooleanField(default=False, help_text='Is this puzzle a meta-puzzle?', verbose_name='Is a metapuzzle')),
                ('puzzle_page_type', models.CharField(choices=[('PDF', 'Puzzle page displays a PDF'), ('LNK', 'Puzzle page links a webpage'), ('WEB', 'Puzzle page displays a webpage')], default='WEB', help_text='The type of webpage for this puzzle.', max_length=3)),
                ('doesnt_count', models.BooleanField(default=False, help_text='Should this puzzle not count towards scoring?')),
                ('puzzle_file', models.FileField(blank=True, help_text='Puzzle file. MUST BE A PDF', storage=hunts.models.PuzzleOverwriteStorage(), upload_to=hunts.models.get_puzzle_file_path)),
                ('resource_file', models.FileField(blank=True, help_text='Puzzle resources, MUST BE A ZIP FILE.', storage=hunts.models.PuzzleOverwriteStorage(), upload_to=hunts.models.get_puzzle_file_path)),
                ('template', models.TextField(default='', help_text='The template string to be rendered to HTML on the puzzle page')),
                ('solution_is_webpage', models.BooleanField(default=False, help_text='Is this solution an html webpage?')),
                ('solution_file', models.FileField(blank=True, help_text='Puzzle solution. MUST BE A PDF.', storage=hunts.models.PuzzleOverwriteStorage(), upload_to=hunts.models.get_solution_file_path)),
                ('solution_resource_file', models.FileField(blank=True, help_text='Puzzle solution resources, MUST BE A ZIP FILE.', storage=hunts.models.PuzzleOverwriteStorage(), upload_to=hunts.models.get_solution_file_path)),
                ('extra_data', models.CharField(blank=True, help_text='A misc. field for any extra data to be stored with the puzzle.', max_length=200)),
                ('num_required_to_unlock', models.IntegerField(default=1, help_text='Number of prerequisite puzzles that need to be solved to unlock this puzzle')),
                ('points_cost', models.IntegerField(default=0, help_text='The number of points needed to unlock this puzzle.')),
                ('points_value', models.IntegerField(default=0, help_text='The number of points this puzzle grants upon solving.')),
                ('episode', models.ForeignKey(help_text='The episode that this puzzle is a part of', on_delete=django.db.models.deletion.CASCADE, to='hunts.episode')),
                ('unlocks', models.ManyToManyField(blank=True, help_text='Puzzles that this puzzle is a possible prerequisite for', to='hunts.Puzzle')),
            ],
            options={
                'verbose_name_plural': '  Puzzles',
                'ordering': ['-episode', 'puzzle_number'],
            },
        ),
        migrations.CreateModel(
            name='Unlockable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.CharField(choices=[('IMG', 'Image'), ('PDF', 'PDF'), ('TXT', 'Text'), ('WEB', 'Link')], default='TXT', help_text="The type of object that is to be unlocked, can be 'IMG', 'PDF', 'TXT', or 'WEB'", max_length=3)),
                ('content', models.CharField(help_text='The link to the content, files must be externally hosted.', max_length=500)),
                ('puzzle', models.ForeignKey(help_text='The puzzle that needs to be solved to unlock this object', on_delete=django.db.models.deletion.CASCADE, to='hunts.puzzle')),
            ],
        ),
        migrations.CreateModel(
            name='Prepuzzle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puzzle_name', models.CharField(help_text='The name of the puzzle as it will be seen by hunt participants', max_length=200)),
                ('released', models.BooleanField(default=False)),
                ('answer', models.CharField(help_text='The answer to the puzzle, not case sensitive', max_length=100)),
                ('template', models.TextField(default='{% extends "puzzle/prepuzzle.html" %}\r\n{% load prepuzzle_tags %}\r\n\r\n{% block content %}\r\n{% endblock content %}', help_text='The template string to be rendered to HTML on the hunt page')),
                ('resource_file', models.FileField(blank=True, help_text='Prepuzzle resources, MUST BE A ZIP FILE.', storage=hunts.models.PuzzleOverwriteStorage(), upload_to=hunts.models.get_prepuzzle_file_path)),
                ('response_string', models.TextField(default='', help_text='Data returned to the webpage for use upon solving.')),
                ('hunt', models.OneToOneField(blank=True, help_text='The hunt that this puzzle is a part of, leave blank for no associated hunt.', null=True, on_delete=django.db.models.deletion.CASCADE, to='hunts.hunt')),
            ],
        ),
        migrations.AddIndex(
            model_name='hunt',
            index=models.Index(fields=['hunt_number'], name='hunts_hunt_hunt_nu_8cdfb2_idx'),
        ),
        migrations.AddField(
            model_name='hint',
            name='eurekas',
            field=models.ManyToManyField(blank=True, help_text='Eurekas that are a prerequisite for shorter time', to='hunts.Eureka', verbose_name='Eureka conditions'),
        ),
        migrations.AddField(
            model_name='hint',
            name='puzzle',
            field=models.ForeignKey(help_text='The puzzle that this automated response is related to', on_delete=django.db.models.deletion.CASCADE, to='hunts.puzzle'),
        ),
        migrations.AddField(
            model_name='eureka',
            name='puzzle',
            field=models.ForeignKey(help_text='The puzzle that this automated response is related to', on_delete=django.db.models.deletion.CASCADE, to='hunts.puzzle'),
        ),
        migrations.AddField(
            model_name='episode',
            name='hunt',
            field=models.ForeignKey(help_text='The hunt that this episode is a part of', on_delete=django.db.models.deletion.CASCADE, to='hunts.hunt'),
        ),
        migrations.AddIndex(
            model_name='puzzle',
            index=models.Index(fields=['puzzle_id'], name='hunts_puzzl_puzzle__e0b697_idx'),
        ),
        migrations.AddIndex(
            model_name='episode',
            index=models.Index(fields=['ep_number'], name='hunts_episo_ep_numb_fb57c6_idx'),
        ),
    ]