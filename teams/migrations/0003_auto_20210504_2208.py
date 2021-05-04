# Generated by Django 3.1.7 on 2021-05-04 20:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hunts', '0002_episode_unlocks'),
        ('teams', '0002_puzzlesolve_duration'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeamEpisodeLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField(help_text='The time the previous episode was finished by this team')),
                ('headstart', models.DurationField(default='00', help_text='The headstart value for this team (HAS NO EFFECT YET)')),
                ('episode', models.ForeignKey(help_text='The episode that can be unlocked when time>episode.start_time-headstart', on_delete=django.db.models.deletion.CASCADE, to='hunts.episode')),
            ],
            options={
                'verbose_name_plural': 'Episodes unlocked by teams',
            },
        ),
        migrations.AlterModelOptions(
            name='flatpageproxyobject',
            options={'verbose_name': 'info page', 'verbose_name_plural': '     Info pages'},
        ),
        migrations.AlterModelOptions(
            name='guess',
            options={'verbose_name_plural': '    Guesses'},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={'verbose_name_plural': '       Persons'},
        ),
        migrations.AlterModelOptions(
            name='puzzlesolve',
            options={'verbose_name_plural': '   Puzzles solved by teams'},
        ),
        migrations.AlterModelOptions(
            name='team',
            options={'verbose_name_plural': '        Teams'},
        ),
        migrations.AlterModelOptions(
            name='teameurekalink',
            options={'verbose_name_plural': ' Eurekas unlocked by teams'},
        ),
        migrations.AlterModelOptions(
            name='teampuzzlelink',
            options={'verbose_name_plural': '  Puzzles unlocked by teams'},
        ),
        migrations.AlterModelOptions(
            name='userproxyobject',
            options={'ordering': ['-pk'], 'verbose_name': 'user', 'verbose_name_plural': '      Users'},
        ),
        migrations.RemoveField(
            model_name='team',
            name='headstarts',
        ),
        migrations.DeleteModel(
            name='TeamHeadstartEpisode',
        ),
        migrations.AddField(
            model_name='teamepisodelink',
            name='team',
            field=models.ForeignKey(help_text='The team that this new episode is for', on_delete=django.db.models.deletion.CASCADE, to='teams.team'),
        ),
        migrations.AddField(
            model_name='team',
            name='ep_unlocked',
            field=models.ManyToManyField(blank=True, help_text='The episodes the team has unlocked', related_name='episodes_for', through='teams.TeamEpisodeLink', to='hunts.Episode'),
        ),
        migrations.AlterUniqueTogether(
            name='teamepisodelink',
            unique_together={('episode', 'team')},
        ),
    ]
