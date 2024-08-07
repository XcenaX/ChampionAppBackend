# Generated by Django 4.2.1 on 2024-04-29 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0048_tournament_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='first_place_prize',
            field=models.IntegerField(blank=True, null=True, verbose_name='Награда за 1 место'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='second_place_prize',
            field=models.IntegerField(blank=True, null=True, verbose_name='Награда за 2 место'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='third_place_prize',
            field=models.IntegerField(blank=True, null=True, verbose_name='Награда за 3 место'),
        ),
    ]
