# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-09-09 17:14
from __future__ import unicode_literals

import django.contrib.auth.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('huntserver', '0022_switch_to_utf8mb4_columns'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProxyObject',
            fields=[
            ],
            options={
                'verbose_name': 'user',
                'proxy': True,
                'verbose_name_plural': 'users',
                'indexes': [],
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]