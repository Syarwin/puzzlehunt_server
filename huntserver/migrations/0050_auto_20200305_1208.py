# Generated by Django 2.2 on 2020-03-05 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('huntserver', '0049_auto_20200215_1930'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='last_received_message',
            field=models.IntegerField(default=0, help_text='The PK of the last message the team has received'),
        ),
        migrations.AlterField(
            model_name='team',
            name='last_seen_message',
            field=models.IntegerField(default=0, help_text='The PK of the last message the team has seen'),
        ),
        migrations.AddIndex(
            model_name='hunt',
            index=models.Index(fields=['hunt_number'], name='huntserver__hunt_nu_0fecf6_idx'),
        ),
        migrations.AddIndex(
            model_name='puzzle',
            index=models.Index(fields=['puzzle_id'], name='huntserver__puzzle__bc16c3_idx'),
        ),
    ]