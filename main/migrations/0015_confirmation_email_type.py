# Generated by Django 4.2.1 on 2024-04-03 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_matchteam_match_teams'),
    ]

    operations = [
        migrations.AddField(
            model_name='confirmation',
            name='email_type',
            field=models.CharField(default='0', max_length=2),
        ),
    ]
