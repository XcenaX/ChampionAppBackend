# Generated by Django 4.2.1 on 2024-04-05 12:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_alter_participant_team_alter_participant_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='match',
            name='participants',
        ),
    ]