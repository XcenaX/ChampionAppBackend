# Generated by Django 4.2.1 on 2024-04-02 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_remove_tournament_users_amateurmatch_city_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='end',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата и время окончания регистрации'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='start',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата и время начала регистрации'),
        ),
    ]
