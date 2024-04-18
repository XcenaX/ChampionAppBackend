from django.db import models
from spacy import blank
from traitlets import default
from main.all_models.tournament import TournamentStage
from main.models import User
from main.all_models.sport import Sport
from main.enums import *


class AmateurMatch(models.Model):
    name = models.CharField(max_length=255, verbose_name='Имя матча')
    description = models.CharField(max_length=500, default="", verbose_name='Описание матча')
    start = models.DateTimeField(verbose_name='Дата и время начала матча')
    address = models.CharField(max_length=255, verbose_name='Адрес')
    lat = models.FloatField(blank=True, null=True, verbose_name='Широта')
    lon = models.FloatField(blank=True, null=True, verbose_name='Долгота')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_amateur_matches', verbose_name='Организатор')
    # photo = models.ImageField(upload_to='amateur_matches_photos/', blank=True, null=True)
    participants = models.ManyToManyField(User, blank=True, null=True, related_name='opponents_amateur_matches', verbose_name='Участники')
    requests = models.ManyToManyField(User, blank=True, null=True, related_name='requests_amateur_matches', verbose_name='Запросы на участие')
    max_participants = models.IntegerField(default=1, verbose_name='Макс кол-во участников')
    auto_accept_participants = models.BooleanField(default=False, verbose_name='Автоматически принимать всех')
    enter_price = models.IntegerField(verbose_name='Цена входа')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта')
    canceled = models.BooleanField(default=False)
    city = models.TextField(default="", verbose_name='Город')
    verified = models.BooleanField(default=False, verbose_name='Подтвержден модерацией')

    def is_full(self):
        return self.max_participants == self.participants.count()+1

    class Meta:
        verbose_name = 'Любительский матч'
        verbose_name_plural = 'Любительские матчи'

    def __str__(self):
        return f"Матч: {self.name}"


class MatchPhoto(models.Model):
    match = models.ForeignKey(AmateurMatch, related_name='photos', on_delete=models.CASCADE)
    photo = models.FileField(upload_to='amateur_matches_photos/')