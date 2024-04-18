# Generated by Django 4.2.1 on 2024-04-01 10:45

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_remove_amateurmatch_status_amateurmatch_canceled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='amateurmatch',
            name='participants',
            field=models.ManyToManyField(blank=True, null=True, related_name='opponents_amateur_matches', to=settings.AUTH_USER_MODEL, verbose_name='Участники'),
        ),
        migrations.AlterField(
            model_name='amateurmatch',
            name='requests',
            field=models.ManyToManyField(blank=True, null=True, related_name='requests_amateur_matches', to=settings.AUTH_USER_MODEL, verbose_name='Запросы на участие'),
        ),
    ]