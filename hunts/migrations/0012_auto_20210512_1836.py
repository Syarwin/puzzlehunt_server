# Generated by Django 3.1.7 on 2021-05-12 16:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hunts', '0011_auto_20210511_1836'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='episode',
            options={'ordering': ['ep_number'], 'verbose_name_plural': '   Episodes'},
        ),
    ]