# Generated by Django 4.2.1 on 2024-04-05 19:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_match_participant1_match_participant2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournament',
            name='participants',
            field=models.ManyToManyField(related_name='participants_tournament', to='main.participant', verbose_name='Участники'),
        ),
    ]
