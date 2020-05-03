# Generated by Django 2.2.11 on 2020-04-24 15:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('huntserver', '0056_auto_20200418_1151'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='team',
            name='last_received_message',
        ),
        migrations.RemoveField(
            model_name='team',
            name='last_seen_message',
        ),
        migrations.AddField(
            model_name='team',
            name='num_waiting_messages',
            field=models.IntegerField(default=0, help_text='The number of unseen messages a team has waiting'),
        ),
    ]