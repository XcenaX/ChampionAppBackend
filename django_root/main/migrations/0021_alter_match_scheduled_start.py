# Generated by Django 4.2.1 on 2024-04-05 19:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_alter_tournament_participants'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='scheduled_start',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Запланированное время начала'),
        ),
    ]
