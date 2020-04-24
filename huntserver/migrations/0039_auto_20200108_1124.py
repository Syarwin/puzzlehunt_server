# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-01-08 16:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('huntserver', '0038_hint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hint',
            name='response',
            field=models.CharField(blank=True, help_text=b'The text of the response to the hint request', max_length=400),
        ),
        migrations.AlterField(
            model_name='hint',
            name='response_time',
            field=models.DateTimeField(help_text=b'Hint request time', null=True),
        ),
    ]