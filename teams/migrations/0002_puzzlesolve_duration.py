# Generated by Django 3.1.7 on 2021-05-04 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='puzzlesolve',
            name='duration',
            field=models.DurationField(default='00', help_text='Time between the puzzle unlocked and its solve'),
        ),
    ]
