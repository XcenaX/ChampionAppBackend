# Generated by Django 4.2.1 on 2024-04-11 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_remove_amateurmatch_photo_matchphoto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='matchphoto',
            name='photo',
            field=models.FileField(upload_to='amateur_matches_photos/'),
        ),
    ]
