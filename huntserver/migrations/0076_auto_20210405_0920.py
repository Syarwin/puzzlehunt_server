# Generated by Django 2.2.18 on 2021-04-05 13:20

import datetime
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('huntserver', '0075_auto_20210404_1737'),
    ]

    operations = [
        migrations.RenameField(
            model_name='eureka',
            old_name='text',
            new_name='answer',
        ),
        migrations.RemoveField(
            model_name='person',
            name='is_shib_acct',
        ),
        migrations.AddField(
            model_name='eureka',
            name='feedback',
            field=models.CharField(blank=True, help_text='The feedback message sent when this eureka is found - if blank, use the default feedback of the hunt', max_length=255),
        ),
        migrations.AddField(
            model_name='hunt',
            name='eureka_feedback',
            field=models.CharField(blank=True, help_text='The default feedback message sent when an eureka is found', max_length=255),
        ),
        migrations.AddField(
            model_name='hunt',
            name='location',
            field=models.CharField(blank=True, help_text='The country the members of the team are from', max_length=80),
        ),
        migrations.AlterField(
            model_name='hint',
            name='short_time',
            field=models.DurationField(help_text='Time after all the associated Eurekas were found', validators=[django.core.validators.MinValueValidator(datetime.timedelta(0))], verbose_name='Shorter Delay'),
        ),
    ]
