# Generated by Django 3.1.7 on 2021-05-03 20:55

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
                ('ep_number', models.IntegerField(help_text='A number used internally for episode sorting, must be unique', unique=True)),
                ('start_date', models.DateTimeField(help_text='The date/time at which this episode will become visible to registered users (without headstarts)')),
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
                ('admin_only', models.BooleanField(default=False, help_text='Only show it in admin panels and not to users')),
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
                ('number_eurekas', models.IntegerField(default=1, help_text='How many Eurekas are reguired to trigger the shorter time', verbose_name='Number required')),
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
                ('is_current_hunt', models.BooleanField(default=False)),
                ('eureka_feedback', models.CharField(blank=True, help_text='The default feedback message sent when an eureka is found', max_length=255)),
            ],
            options={
                'verbose_name_plural': '    Hunts',
            },
        ),
        migrations.CreateModel(
            name='Puzzle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puzzle_name', models.CharField(help_text='The name of the puzzle as it will be seen by hunt participants', max_length=200)),
                ('puzzle_number', models.IntegerField(default=1, help_text='The number of the puzzle within the episode, for sorting purposes (must be unique within the episode, and not too large)')),
                ('puzzle_id', models.CharField(help_text='A 3-12 characters string that uniquely identifies the puzzle', max_length=12, unique=True)),
                ('answer', models.CharField(help_text='The answer to the puzzle, not case nor space sensitive. Can contain parentheses to show multiple options but a regex is then mandatory.', max_length=100)),
                ('answer_regex', models.CharField(blank=True, default='', help_text='The regexp towards which the guess is checked in addition to the answer (optional)', max_length=100)),
                ('template', models.TextField(default='', help_text='The template string to be rendered to HTML on the puzzle page')),
                ('extra_data', models.CharField(blank=True, help_text='A misc. field for any extra data to be stored with the puzzle.', max_length=200)),
                ('num_required_to_unlock', models.IntegerField(default=1, help_text='Number of prerequisite puzzles that need to be solved to unlock this puzzle')),
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
            name='SolutionFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(blank=True, help_text='Include the URL of the file in puzzle content using $slug or ${slug}.', max_length=50, null=True, verbose_name='Template Slug')),
                ('url_path', models.CharField(help_text='The file path you want to appear in the URL. Can include "directories" using /', max_length=50, verbose_name='URL Filename')),
                ('file', models.FileField(help_text='The extension of the uploaded file will determine the Content-Type of the file when served', upload_to=hunts.models.solution_file_path)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hunts.puzzle')),
            ],
        ),
        migrations.CreateModel(
            name='PuzzleFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(blank=True, help_text='Include the URL of the file in puzzle content using $slug or ${slug}.', max_length=50, null=True, verbose_name='Template Slug')),
                ('url_path', models.CharField(help_text='The file path you want to appear in the URL. Can include "directories" using /', max_length=50, verbose_name='URL Filename')),
                ('file', models.FileField(help_text='The extension of the uploaded file will determine the Content-Type of the file when served', upload_to=hunts.models.puzzle_file_path)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hunts.puzzle')),
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
        migrations.AlterUniqueTogether(
            name='solutionfile',
            unique_together={('puzzle', 'slug'), ('puzzle', 'url_path')},
        ),
        migrations.AlterUniqueTogether(
            name='puzzlefile',
            unique_together={('puzzle', 'slug'), ('puzzle', 'url_path')},
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
