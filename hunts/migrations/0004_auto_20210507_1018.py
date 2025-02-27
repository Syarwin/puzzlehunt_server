# Generated by Django 3.1.7 on 2021-05-07 08:18

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('hunts', '0003_auto_20210507_0826'),
    ]

    operations = [
        migrations.CreateModel(
            name='APIToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False)),
            ],
        ),
        migrations.AddField(
            model_name='hunt',
            name='discord_bot_id',
            field=models.BigIntegerField(blank=True, default='0', help_text='Dicord bot id, leave blank or zero if none is dedicated to the hunt', null=True),
        ),
        migrations.AddField(
            model_name='hunt',
            name='discord_url',
            field=models.URLField(blank=True, default='', help_text='URL of the discord server, leave empty is none is dedicated to the hunt'),
        ),
    ]
