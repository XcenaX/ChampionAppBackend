# Generated by Django 4.2.1 on 2024-04-29 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0044_tournament_participants_in_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='register_open_until',
            field=models.TextField(default='', verbose_name='Регистрация открыта до...'),
        ),
        migrations.AlterField(
            model_name='tournament',
            name='end',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Дата и время окончания турнира'),
        ),
        migrations.AlterField(
            model_name='tournament',
            name='start',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Дата и время начала турнира'),
        ),
    ]
