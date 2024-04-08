# Generated by Django 4.2.1 on 2024-04-05 12:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_remove_match_participants'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='participant1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='match_participant1', to='main.participant', verbose_name='Участник 1'),
        ),
        migrations.AddField(
            model_name='match',
            name='participant2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='match_participant2', to='main.participant', verbose_name='Участник 2'),
        ),
    ]
